"""Pipeline de extracción de datos de proformas/facturas.

S2 incluye un extractor heurístico sobre TEXTO (proformas en texto/CSV y PDFs con
capa de texto). Para PDFs escaneados/imágenes hace falta un OCR/Document AI real:
ese es un adapter enchufable (implementa el Protocol `Extractor`) que se conectará
cuando se decida el proveedor. NO se inventan datos: lo no reconocido queda con
baja confianza para revisión humana.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Protocol

MODEL_VERSION = "heuristic-text-v1"

INCOTERMS = ["EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"]
CURRENCIES = ["USD", "EUR", "CNY", "RMB", "MXN", "COP", "PEN", "BRL", "JPY", "GBP"]


@dataclass
class ExtractedField:
    field_name: str
    value: str | None
    confidence: float
    source_page: int | None = None


@dataclass
class ExtractionResult:
    fields: list[ExtractedField] = field(default_factory=list)
    model_version: str = MODEL_VERSION


class Extractor(Protocol):
    def extract(self, data: bytes, content_type: str | None, filename: str | None) -> ExtractionResult: ...


def _text_from(data: bytes, content_type: str | None, filename: str | None) -> tuple[str, int]:
    name = (filename or "").lower()
    is_pdf = "pdf" in (content_type or "").lower() or name.endswith(".pdf")
    if is_pdf:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return text, len(reader.pages)
        except Exception:
            return "", 1
    return data.decode("utf-8", errors="replace"), 1


class HeuristicProformaExtractor:
    """Extractor por reglas/regex sobre texto. Determinista y explicable."""

    def extract(
        self, data: bytes, content_type: str | None, filename: str | None
    ) -> ExtractionResult:
        text, pages = _text_from(data, content_type, filename)
        result = ExtractionResult()
        upper = text.upper()

        def add(name: str, value: str | None, conf: float) -> None:
            result.fields.append(ExtractedField(name, value, round(conf, 2), source_page=1))

        # invoice_number: palabra clave, luego (opcional "No"/"#"/...) y un ':' o '#'
        # antes del identificador, sin cruzar saltos de línea.
        m = re.search(
            r"(?:invoice|factura|proforma)[^\n:#]*?[:#]\s*([A-Z0-9][A-Z0-9\-/]{3,})",
            text,
            re.IGNORECASE,
        )
        add("invoice_number", m.group(1).strip() if m else None, 0.85 if m else 0.0)

        # incoterm
        found_inco = next((i for i in INCOTERMS if re.search(rf"\b{i}\b", upper)), None)
        add("incoterm", found_inco, 0.8 if found_inco else 0.0)

        # currency
        found_cur = next((c for c in CURRENCIES if re.search(rf"\b{c}\b", upper)), None)
        add("currency", found_cur, 0.75 if found_cur else 0.0)

        # total amount
        mt = re.search(
            r"(?:grand\s+total|total\s+amount|total)\s*[:\-]?\s*(?:USD|EUR|\$|€)?\s*"
            r"([0-9][0-9.,]*\.?[0-9]{0,2})",
            text,
            re.IGNORECASE,
        )
        add("total_amount", mt.group(1).replace(",", "") if mt else None, 0.7 if mt else 0.0)

        # date (formatos comunes)
        md = re.search(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", text)
        add("date", md.group(1) if md else None, 0.6 if md else 0.0)

        # count de líneas con precio (aproximación al nº de ítems)
        line_items = len(re.findall(r"\d+\s*[xX]?\s*[\d.,]+\s*(?:USD|EUR|\$)?", text))
        add("line_item_count", str(line_items) if line_items else None, 0.4 if line_items else 0.0)

        result.model_version = MODEL_VERSION + (f"+pdf({pages}p)" if pages else "")
        return result


_extractor: Extractor | None = None


def get_extractor() -> Extractor:
    """Dependencia FastAPI. Sustituible por un adapter de OCR/Document AI real."""
    global _extractor
    if _extractor is None:
        _extractor = HeuristicProformaExtractor()
    return _extractor
