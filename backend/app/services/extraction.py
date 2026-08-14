"""Pipeline de extracción de datos de proformas/facturas y documentos escaneados.

Dos capas desacopladas:

1. **Adquisición de texto** (`acquire_text`): obtiene texto del documento.
   - Texto/CSV: directo.
   - PDF con capa de texto: `pypdf`.
   - PDF escaneado o imagen: OCR real con Tesseract (`pytesseract` + `pypdfium2`).
     Si las librerías/el binario de OCR no están disponibles, degrada con elegancia
     (devuelve el texto que haya, sin fallar) y los campos quedan con baja confianza.

2. **Extracción de campos** (`extract_fields_from_text`): reglas/regex deterministas
   y explicables sobre el texto. NO se inventan datos: lo no reconocido queda con
   confianza 0 para revisión humana (human-by-exception).

El extractor por defecto (`get_extractor`) es OCR-capaz y se controla con
`settings.ocr_enabled`.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)

TEXT_MODEL_VERSION = "heuristic-text-v1"
OCR_MODEL_VERSION = "ocr-tesseract-v1"

INCOTERMS = ["EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"]
CURRENCIES = ["USD", "EUR", "CNY", "RMB", "MXN", "COP", "PEN", "BRL", "JPY", "GBP"]

_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif")


@dataclass
class ExtractedField:
    field_name: str
    value: str | None
    confidence: float
    source_page: int | None = None


@dataclass
class ExtractionResult:
    fields: list[ExtractedField] = field(default_factory=list)
    model_version: str = TEXT_MODEL_VERSION


class Extractor(Protocol):
    def extract(self, data: bytes, content_type: str | None, filename: str | None) -> ExtractionResult: ...


# --------------------------------------------------------------------------- #
#  Capa 1: adquisición de texto (con OCR real como respaldo)
# --------------------------------------------------------------------------- #
def _pdf_text_layer(data: bytes) -> tuple[str, int]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text, len(reader.pages)
    except Exception:  # noqa: BLE001
        return "", 1


def _ocr_image(data: bytes) -> str:
    """OCR de una imagen en bytes. Devuelve "" si el stack de OCR no está disponible."""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img, lang=settings.ocr_languages)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR de imagen no disponible: %s", exc)
        return ""


def _ocr_pdf(data: bytes, max_pages: int = 10) -> str:
    """Rasteriza el PDF (pypdfium2, sin poppler) y aplica OCR (Tesseract) página a página."""
    try:
        import pypdfium2 as pdfium
        import pytesseract

        pdf = pdfium.PdfDocument(data)
        chunks: list[str] = []
        n = min(len(pdf), max_pages)
        for i in range(n):
            page = pdf[i]
            bitmap = page.render(scale=2.0)  # ~144 dpi, suficiente para facturas
            pil = bitmap.to_pil()
            chunks.append(pytesseract.image_to_string(pil, lang=settings.ocr_languages))
        return "\n".join(chunks)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR de PDF no disponible: %s", exc)
        return ""


def acquire_text(
    data: bytes, content_type: str | None, filename: str | None, ocr_enabled: bool
) -> tuple[str, int, str]:
    """Devuelve (texto, nº_páginas, método). método ∈ {text, pdf-text, ocr, image-no-ocr}."""
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    is_pdf = "pdf" in ctype or name.endswith(".pdf")
    is_image = ctype.startswith("image/") or name.endswith(_IMAGE_EXT)

    if is_pdf:
        text, pages = _pdf_text_layer(data)
        # Un PDF con muy poco texto suele ser escaneado -> intentamos OCR.
        if ocr_enabled and len(text.strip()) < 20:
            ocr = _ocr_pdf(data)
            if ocr.strip():
                return ocr, pages, "ocr"
        return text, pages, "pdf-text"

    if is_image:
        if ocr_enabled:
            ocr = _ocr_image(data)
            if ocr.strip():
                return ocr, 1, "ocr"
        return "", 1, "image-no-ocr"

    return data.decode("utf-8", errors="replace"), 1, "text"


# --------------------------------------------------------------------------- #
#  Capa 2: extracción de campos (reglas deterministas sobre texto)
# --------------------------------------------------------------------------- #
def extract_fields_from_text(text: str) -> ExtractionResult:
    result = ExtractionResult()
    upper = text.upper()

    def add(name: str, value: str | None, conf: float) -> None:
        result.fields.append(ExtractedField(name, value, round(conf, 2), source_page=1))

    # invoice_number: palabra clave + separador (: o #), sin cruzar saltos de línea.
    m = re.search(
        r"(?:invoice|factura|proforma)[^\n:#]*?[:#]\s*([A-Z0-9][A-Z0-9\-/]{3,})",
        text,
        re.IGNORECASE,
    )
    add("invoice_number", m.group(1).strip() if m else None, 0.85 if m else 0.0)

    # supplier_name: primera línea no vacía y "razonable" (heurística de baja confianza).
    supplier = None
    for line in (ln.strip() for ln in text.splitlines()):
        if 3 <= len(line) <= 80 and not re.match(r"(?i)^(invoice|factura|proforma|date|fecha)\b", line):
            supplier = line
            break
    add("supplier_name", supplier, 0.4 if supplier else 0.0)

    found_inco = next((i for i in INCOTERMS if re.search(rf"\b{i}\b", upper)), None)
    add("incoterm", found_inco, 0.8 if found_inco else 0.0)

    found_cur = next((c for c in CURRENCIES if re.search(rf"\b{c}\b", upper)), None)
    add("currency", found_cur, 0.75 if found_cur else 0.0)

    mt = re.search(
        r"(?:grand\s+total|total\s+amount|total)\s*[:\-]?\s*(?:USD|EUR|\$|€)?\s*"
        r"([0-9][0-9.,]*\.?[0-9]{0,2})",
        text,
        re.IGNORECASE,
    )
    add("total_amount", mt.group(1).replace(",", "") if mt else None, 0.7 if mt else 0.0)

    md = re.search(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", text)
    add("date", md.group(1) if md else None, 0.6 if md else 0.0)

    line_items = len(re.findall(r"\d+\s*[xX]?\s*[\d.,]+\s*(?:USD|EUR|\$)?", text))
    add("line_item_count", str(line_items) if line_items else None, 0.4 if line_items else 0.0)

    return result


# --------------------------------------------------------------------------- #
#  Extractores
# --------------------------------------------------------------------------- #
class HeuristicProformaExtractor:
    """Extractor SOLO texto (texto/CSV y PDFs con capa de texto). Determinista."""

    def extract(self, data: bytes, content_type: str | None, filename: str | None) -> ExtractionResult:
        text, pages, _ = acquire_text(data, content_type, filename, ocr_enabled=False)
        result = extract_fields_from_text(text)
        result.model_version = TEXT_MODEL_VERSION + (f"+pdf({pages}p)" if pages else "")
        return result


class OcrExtractor:
    """Extractor OCR-capaz: capa de texto primero, OCR real (Tesseract) como respaldo."""

    def extract(self, data: bytes, content_type: str | None, filename: str | None) -> ExtractionResult:
        text, pages, method = acquire_text(data, content_type, filename, ocr_enabled=settings.ocr_enabled)
        result = extract_fields_from_text(text)
        base = OCR_MODEL_VERSION if method == "ocr" else TEXT_MODEL_VERSION
        result.model_version = base + (f"+pdf({pages}p)" if pages and pages > 1 else "")
        return result


_extractor: Extractor | None = None


def get_extractor() -> Extractor:
    """Dependencia FastAPI. OCR-capaz por defecto; conmutable con settings.ocr_enabled."""
    global _extractor
    if _extractor is None:
        _extractor = OcrExtractor() if settings.ocr_enabled else HeuristicProformaExtractor()
    return _extractor
