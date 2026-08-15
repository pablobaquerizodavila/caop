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
class LineItem:
    """Ítem de una proforma/factura extraído del texto. Sin inventar: campos no
    reconocidos quedan en None y la confianza refleja la calidad de la lectura."""
    description: str | None = None
    model: str | None = None
    hs_code: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    amount: str | None = None
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    fields: list[ExtractedField] = field(default_factory=list)
    line_items: list[LineItem] = field(default_factory=list)
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
#  Capa 2b: extracción de ÍTEMS línea por línea (proformas / facturas)
# --------------------------------------------------------------------------- #
_HS_INLINE = re.compile(r"\b(\d{4}\.\d{2}(?:\.\d{2}){0,3}|\d{6,10})\b")
_LINE_NUM_PREFIX = re.compile(r"^\s*(\d{1,3})[\).\-]?\s+")
_NUMTOK = re.compile(r"[-+]?\d[\d.,]*")

_COL_QTY = re.compile(
    r"\b(qty|quantity|cantidad|cant|units?(?!\s*(?:price|precio|cost))|unidades|pcs|pzas?)\b",
    re.I,
)
_COL_UNIT = re.compile(
    r"(unit\s*price|precio\s*unit\w*|p\.?\s*unit|unit\s*cost|u\.?\s*price|"
    r"precio\s*x\s*unidad|price/unit|valor\s*unit\w*|\bprice\b|\bprecio\b)",
    re.I,
)
_COL_AMT = re.compile(r"\b(amount|importe|monto|value|valor|line\s*total|ext\w*|total)\b", re.I)
_COL_DESC = re.compile(
    r"\b(description|descripci[oó]n|item|product\w*|art[ií]culo|detalle|goods|"
    r"mercanc[ií]a|concepto)\b",
    re.I,
)
_COL_MODEL = re.compile(
    r"\b(model[oa]?|part\s*(?:no\.?|number|#)?|part-?no|c[oó]digo|item\s*(?:code|no\.?|#)|"
    r"ref\.?(?:erencia)?|sku|cat\.?\s*(?:no\.?|#)?|n[°º]\s*parte|style)\b",
    re.I,
)
_COL_HS = re.compile(
    r"\b(hs\s*code|h\.?s\.?|sub\s*partida|partida|arancel\w*|nandina|naladisa|tariff\s*code|"
    r"c[oó]d\.?\s*arancel\w*)\b",
    re.I,
)
_STOP_LINE = re.compile(
    r"\b(sub\s*total|subtotal|grand\s+total|total\s+amount|amount\s+due|balance\s+due|"
    r"freight|flete|insurance|seguro|shipping|discount|descuento|\btax\b|\biva\b|\bvat\b|"
    r"packing|handling)\b",
    re.I,
)
# Líneas de encabezado/pie del documento que NO son ítems (defensa anti falsos positivos).
_LABEL_LINE = re.compile(
    r"^\s*(invoice|factura|proforma|date|fecha|incoterm|currency|moneda|supplier|vendor|"
    r"seller|buyer|bill\s*to|ship\s*to|sold\s*to|customer|cliente|tel|phone|e-?mail|"
    r"address|direcci[oó]n|\bruc\b|tax\s*id|payment|terms|order\s*no|po\s*no|page)\b",
    re.I,
)


def _parse_number(tok: str) -> float | None:
    """Normaliza un número en formato US (1,234.56) o europeo (1.234,56)."""
    tok = tok.strip()
    if not re.fullmatch(r"[-+]?[\d.,]+", tok) or not any(c.isdigit() for c in tok):
        return None
    neg = tok.startswith("-")
    t = tok.lstrip("+-")
    has_dot, has_comma = "." in t, "," in t
    try:
        if has_dot and has_comma:
            # El separador más a la derecha es el decimal.
            if t.rfind(".") > t.rfind(","):
                t = t.replace(",", "")            # 1,234.56
            else:
                t = t.replace(".", "").replace(",", ".")  # 1.234,56
        elif has_comma:
            parts = t.split(",")
            if len(parts) > 2 or len(parts[-1]) == 3:
                t = t.replace(",", "")            # 1,000 / 1,000,000 -> miles
            else:
                t = parts[0] + "." + parts[-1]    # 0,25 -> decimal
        elif has_dot and t.count(".") > 1:
            t = t.replace(".", "")                # 1.000.000 -> miles
        val = float(t)
        return -val if neg else val
    except ValueError:
        return None


def _fmt_num(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _detect_column_order(header: str) -> list[str] | None:
    """De una línea de cabecera devuelve el orden L→R de las columnas de valor
    reconocidas entre {qty, unit_price, amount}, o None si no parece cabecera."""
    hits: list[tuple[int, str]] = []
    for rx, key in ((_COL_QTY, "quantity"), (_COL_UNIT, "unit_price"), (_COL_AMT, "amount")):
        m = rx.search(header)
        if m:
            hits.append((m.start(), key))
    has_desc = _COL_DESC.search(header) is not None
    # Cabecera creíble: descripción + ≥1 columna de valor, o ≥2 columnas de valor,
    # y sin exceso de dígitos (las cabeceras casi no llevan números).
    digits = sum(c.isdigit() for c in header)
    if digits > 4:
        return None
    if (has_desc and hits) or len(hits) >= 2:
        # dedup preservando la 1ª aparición de cada key, ordenado por posición
        hits.sort(key=lambda h: h[0])
        seen: set[str] = set()
        order = [k for _, k in hits if not (k in seen or seen.add(k))]
        return order
    return None


def _parse_item_line(line: str, order: list[str] | None) -> LineItem | None:
    if not line.strip() or _STOP_LINE.search(line) or _LABEL_LINE.match(line):
        return None
    body = line
    hs = None
    mhs = _HS_INLINE.search(body)
    if mhs:
        hs = mhs.group(1)
        body = body[: mhs.start()] + "  " + body[mhs.end():]
    body = _LINE_NUM_PREFIX.sub("", body)

    toks = [(m, _parse_number(m.group(0))) for m in _NUMTOK.finditer(body)]
    vals = [(m, v) for m, v in toks if v is not None]
    if len(vals) < 2:
        return None  # una línea de ítem trae al menos cantidad + un precio

    n = len(order) if order else 0
    conf = 0.0
    qty = unit = amount = None

    def whole_positive(x: float) -> bool:
        return x > 0 and abs(x - round(x)) < 1e-9

    if order:
        take = vals[-min(n, 3):]
        keys = order[-len(take):]
        mapping = dict(zip(keys, [v for _, v in take]))
        qty = mapping.get("quantity")
        unit = mapping.get("unit_price")
        amount = mapping.get("amount")
        first = take[0][0].start()
        conf = 0.6
        if qty is not None and unit is not None and amount is not None:
            conf = 0.78 if abs(qty * unit - amount) <= max(0.02 * abs(amount), 0.01) else 0.55
    else:
        # Sin cabecera: heurística por los números al final de la línea.
        last3 = vals[-3:]
        if len(last3) == 3:
            a, b, c = (v for _, v in last3)
            if abs(a * b - c) <= max(0.02 * abs(c), 0.01):
                qty, unit, amount = a, b, c
                first = last3[0][0].start()
                conf = 0.6
            else:
                qty, unit = a, b  # asume Cant. | P.unit | (importe dudoso)
                first = last3[0][0].start()
                conf = 0.35
        else:
            (mq, qv), (mu, uv) = vals[-2:]
            qty, unit = qv, uv
            first = mq.start()
            conf = 0.35

    # Plausibilidad: un ítem real tiene cantidad > 0 y precio ≥ 0 (filtra fechas,
    # números de folio y otras líneas de encabezado que colaron 2 números).
    if qty is None or qty <= 0 or unit is None or unit < 0:
        return None
    if amount is not None and amount < 0:
        return None

    desc = body[:first].strip(" .:-|\t")
    if not any(ch.isalpha() for ch in desc):
        return None  # sin texto no es un ítem (evita filas de totales/números sueltos)
    if not whole_positive(qty) and unit > qty:
        # cantidad y precio probablemente invertidos (qty decimal < precio): baja confianza
        conf = min(conf, 0.4)

    return LineItem(
        description=desc[:200] or None,
        hs_code=hs,
        quantity=_fmt_num(qty) if qty is not None else None,
        unit_price=_fmt_num(unit) if unit is not None else None,
        amount=_fmt_num(amount) if amount is not None else None,
        confidence=round(conf, 2),
    )


# --- Matching por columnas: mapea las columnas del documento a los campos de la
#     plantilla (modelo/descripción/cantidad/precio) por la posición de la cabecera. ---
_LINE_NUM_ONLY = re.compile(r"^\s*(\d{1,3})[\).\-]?\s+")


def _detect_columns(header: str) -> list[tuple[int, str]] | None:
    """Detecta columnas en la cabecera y su posición. Devuelve [(pos, key), …]
    ordenado L→R, o None si no parece una cabecera de tabla de ítems.

    Reconoce (ES/EN + sinónimos): modelo, descripción, subpartida (HS), cantidad,
    precio unitario e importe. Resuelve solapes por prioridad."""
    digits = sum(c.isdigit() for c in header)
    if digits > 6:
        return None
    raw: list[tuple[int, int, str]] = []  # (start, priority, key)
    for rx, key, pr in (
        (_COL_MODEL, "model", 0),
        (_COL_HS, "hs_code", 1),
        (_COL_UNIT, "unit_price", 2),
        (_COL_AMT, "amount", 3),
        (_COL_QTY, "quantity", 4),
        (_COL_DESC, "description", 5),
    ):
        m = rx.search(header)
        if m:
            raw.append((m.start(), pr, key))
    raw.sort()  # por posición y, en empate, por prioridad (menor = más específico)
    cols: list[tuple[int, str]] = []
    seen: set[str] = set()
    for start, _pr, key in raw:
        if key in seen:
            continue
        if cols and abs(start - cols[-1][0]) <= 3:
            continue  # otra etiqueta pegada a una ya tomada → se descarta la de menor prioridad
        cols.append((start, key))
        seen.add(key)
    cols.sort()
    keys = {k for _, k in cols}
    if not ({"description", "model"} & keys):
        return None
    # Exige ≥2 columnas de valor para no confundir cabeceras partidas/parciales
    # (p. ej. una línea "Model QTY") con una tabla real alineada.
    if len({"quantity", "unit_price", "amount"} & keys) < 2:
        return None
    return cols


def _num_in(text: str) -> float | None:
    """Último número normalizado dentro de una celda (o None)."""
    vals = [_parse_number(m.group(0)) for m in _NUMTOK.finditer(text or "")]
    vals = [v for v in vals if v is not None]
    return vals[-1] if vals else None


def _item_from_columns(line: str, cols: list[tuple[int, str]]) -> LineItem | None:
    if not line.strip() or _STOP_LINE.search(line) or _LABEL_LINE.match(line):
        return None
    # Corta la línea en celdas según las posiciones de la cabecera.
    cells: dict[str, str] = {}
    n = len(cols)
    for i, (start, key) in enumerate(cols):
        lo = 0 if i == 0 else start
        hi = cols[i + 1][0] if i + 1 < n else len(line)
        cells[key] = line[lo:hi]

    qty = _num_in(cells.get("quantity", ""))
    unit = _num_in(cells.get("unit_price", ""))
    amount = _num_in(cells.get("amount", ""))
    model = (cells.get("model") or "").strip(" .:-|\t")
    desc = (cells.get("description") or "").strip(" .:-|\t")
    # La primera celda suele arrastrar el nº de línea ("1  ..."): se quita.
    if cols and cols[0][1] == "model":
        model = _LINE_NUM_ONLY.sub("", model).strip(" .:-|\t")
    elif cols and cols[0][1] == "description":
        desc = _LINE_NUM_ONLY.sub("", desc).strip(" .:-|\t")

    hs = None
    hs_cell = cells.get("hs_code")
    mhs = _HS_INLINE.search(hs_cell) if hs_cell else _HS_INLINE.search(line)
    if mhs:
        hs = mhs.group(1)

    # Si no hay columna de precio unitario pero sí importe y cantidad, se deriva
    # por aritmética (no es inventar: importe/cantidad).
    if unit is None and amount is not None and qty:
        unit = amount / qty

    if qty is None or qty <= 0 or unit is None or unit < 0:
        return None
    if amount is not None and amount < 0:
        return None
    if not (any(c.isalpha() for c in desc) or any(c.isalpha() for c in model)):
        return None  # ni descripción ni modelo con texto → no es un ítem

    conf = 0.7
    if amount is not None and abs(qty * unit - amount) <= max(0.02 * abs(amount), 0.01):
        conf = 0.82

    return LineItem(
        description=desc[:200] or None,
        model=model[:120] or None,
        hs_code=hs,
        quantity=_fmt_num(qty),
        unit_price=_fmt_num(unit),
        amount=_fmt_num(amount) if amount is not None else None,
        confidence=round(conf, 2),
    )


_CUR = re.compile(r"[$€]")


def _money_val(tok: str) -> tuple[float | None, bool]:
    """Devuelve (valor, es_monto). 'es_monto' si trae símbolo de moneda o decimales."""
    s = tok.strip()
    has_cur = bool(_CUR.search(s))
    s2 = _CUR.sub("", s).strip()
    v = _parse_number(s2)
    if v is None:
        return None, False
    is_money = has_cur or bool(re.search(r"[.,]\d{2}$", s2))
    return v, is_money


def _parse_row_freeform(line: str) -> LineItem | None:
    """Respaldo para filas sin columnas alineadas (texto de PDF colapsado).

    Ancla en los montos: precio unitario e importe son los tokens con moneda /
    decimales al final; la cantidad es el entero justo antes; lo de la izquierda
    es el modelo/descripción. Maneja que el modelo tenga números (p. ej. PV33-6048).
    """
    if not line.strip() or _STOP_LINE.search(line) or _LABEL_LINE.match(line):
        return None
    body = line
    hs = None
    mhs = _HS_INLINE.search(body)
    if mhs:
        hs = mhs.group(1)
        body = body[: mhs.start()] + " " + body[mhs.end():]

    toks = [m.group(0) for m in re.finditer(r"\S+", body)]
    if not toks:
        return None
    # Quita el nº de línea al inicio ("1", "1)", "1.").
    if re.fullmatch(r"\d{1,3}[\).\-]?", toks[0]):
        toks = toks[1:]
    if not toks:
        return None

    # Montos contiguos al final de la fila.
    money: list[tuple[int, float]] = []
    i = len(toks) - 1
    while i >= 0:
        v, ism = _money_val(toks[i])
        if ism and v is not None:
            money.append((i, v))
            i -= 1
        else:
            break
    if not money:
        return None
    money.reverse()
    first_money_idx = money[0][0]
    if len(money) >= 2:
        unit, amount = money[-2][1], money[-1][1]
    else:
        unit, amount = money[-1][1], None

    # Cantidad: último número "plano" (sin moneda/decimales) antes del primer monto.
    qty = None
    qty_idx = None
    for j in range(first_money_idx - 1, -1, -1):
        v, ism = _money_val(toks[j])
        if v is not None and not ism:
            qty, qty_idx = v, j
            break
    if qty is None or qty <= 0 or unit is None or unit < 0:
        return None

    text = " ".join(toks[:qty_idx]).strip(" .:-|") if qty_idx is not None else ""
    if not any(c.isalpha() for c in text):
        return None

    # ¿El texto parece un modelo (código con letras+dígitos o guion) o una descripción?
    first = text.split()[0] if text.split() else ""
    looks_model = bool(re.search(r"[A-Za-z]", first) and re.search(r"\d", first)) or "-" in first
    conf = 0.55
    if amount is not None and abs(qty * unit - amount) <= max(0.02 * abs(amount), 0.01):
        conf = 0.72
    return LineItem(
        description=None if looks_model else text[:200],
        model=text[:120] if looks_model else None,
        hs_code=hs,
        quantity=_fmt_num(qty),
        unit_price=_fmt_num(unit),
        amount=_fmt_num(amount) if amount is not None else None,
        confidence=round(conf, 2),
    )


def extract_line_items_from_text(text: str, max_items: int = 60) -> list[LineItem]:
    """Extrae ítems de una proforma/factura. Determinista y explicable.

    1) Detecta la cabecera y hace *matching* de columnas (modelo, descripción,
       cantidad, precio, importe, subpartida) por su posición, cortando cada fila
       en celdas. Funciona con tablas alineadas (ES/EN + sinónimos).
    2) Si no hay cabecera alineada (o no dio ítems), usa un respaldo anclado en los
       montos ($/decimales), útil cuando el PDF colapsa la tabla a texto plano.
    No inventa: lo no reconocido queda en None.
    """
    lines = text.splitlines()

    # (1) Matching por columnas si hay una cabecera alineada con nombres.
    cols: list[tuple[int, str]] | None = None
    header_idx = -1
    for i, ln in enumerate(lines):
        c = _detect_columns(ln)
        if c:
            cols, header_idx = c, i
            break

    items: list[LineItem] = []
    if cols:
        for ln in lines[header_idx + 1:]:
            if _STOP_LINE.search(ln):
                break  # zona de totales cierra la tabla
            it = _item_from_columns(ln, cols)
            if it:
                items.append(it)
                if len(items) >= max_items:
                    break
        if items:
            return items  # si no dio ítems, cae al respaldo de abajo

    # (2) Respaldo anclado en montos (filas con texto colapsado).
    for ln in lines:
        it = _parse_row_freeform(ln)
        if it:
            items.append(it)
            if len(items) >= max_items:
                break
    if items:
        return items

    # (3) Última heurística por posición de los números (sin modelo).
    order: list[str] | None = None
    for ln in lines:
        od = _detect_column_order(ln)
        if od:
            order = od
            break
    for ln in lines:
        it = _parse_item_line(ln, order)
        if it:
            items.append(it)
            if len(items) >= max_items:
                break
    return items


def _norm_date(s: str | None) -> str | None:
    """Normaliza fechas comunes a ISO (asume dd/mm/aaaa en formatos ambiguos)."""
    if not s:
        return None
    s = s.strip()
    m = re.match(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", s)
    if m:
        d, mo, y = m.groups()
        year = int(y)
        year = 2000 + year if year < 100 else year
        return f"{year:04d}-{int(mo):02d}-{int(d):02d}"
    return None


def _label_value(text: str, labels: list[str], value_pat: str) -> str | None:
    """Busca 'etiqueta: valor' para la primera etiqueta que aparezca."""
    for lab in labels:
        m = re.search(rf"{lab}\s*[:#.\-]?\s*({value_pat})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip(" .:-")
    return None


def extract_transport_from_text(text: str) -> ExtractionResult:
    """Extrae datos de transporte de un BL / AWB (por etiquetas). Baja/media confianza."""
    result = ExtractionResult()
    ALNUM = r"[A-Z0-9][A-Z0-9\- /]{2,40}"
    WORDS = r"[A-Za-z0-9][A-Za-z0-9\-\. /]{2,48}"
    DATEV = r"\d{1,4}[-/.]\d{1,2}[-/.]\d{2,4}"

    def add(name: str, value: str | None, conf: float) -> None:
        result.fields.append(ExtractedField(name, value, round(conf, 2), source_page=1))

    add("carrier", _label_value(text, [r"\bcarrier\b", r"\bnaviera\b",
        r"shipping\s+line", r"l[ií]nea\s+naviera", r"airline", r"aerol[ií]nea"], WORDS), 0.5)
    add("bl_number", _label_value(text, [r"master\s*b/?l(?:\s*no)?", r"\bmbl\b",
        r"house\s*b/?l(?:\s*no)?", r"\bhbl\b", r"bill\s+of\s+lading(?:\s*no)?", r"b/?l\s*no",
        r"master\s*awb", r"\bmawb\b", r"house\s*awb", r"\bhawb\b", r"\bawb\s*no", r"gu[ií]a"],
        ALNUM), 0.6)
    add("vessel", _label_value(text, [r"ocean\s+vessel", r"\bvessel\b", r"\bbuque\b",
        r"motonave", r"\bm/?v\b"], WORDS), 0.5)
    add("voyage", _label_value(text, [r"\bvoyage\b", r"\bvoy\b", r"\bviaje\b"],
        r"[A-Z0-9][A-Z0-9\-]{0,10}"), 0.5)
    add("flight_number", _label_value(text, [r"\bflight\b", r"\bvuelo\b", r"\bfl\s*no"],
        r"[A-Z]{2}\s?\d{2,4}"), 0.5)
    add("pol", _label_value(text, [r"port\s+of\s+loading", r"puerto\s+de\s+embarque",
        r"\bpol\b", r"place\s+of\s+receipt"], WORDS), 0.5)
    add("pod", _label_value(text, [r"port\s+of\s+discharge", r"puerto\s+de\s+descarga",
        r"\bpod\b", r"place\s+of\s+delivery", r"destino"], WORDS), 0.5)
    add("etd", _norm_date(_label_value(text, [r"\betd\b", r"shipped\s+on\s+board",
        r"on\s*board\s+date", r"fecha\s+de\s+embarque", r"date\s+of\s+departure"], DATEV)), 0.5)
    add("eta", _norm_date(_label_value(text, [r"\beta\b", r"estimated\s+arrival",
        r"fecha\s+estimada\s+de\s+arribo", r"arrival\s+date"], DATEV)), 0.5)

    # Confianza 0 cuando no se reconoció el campo.
    for f in result.fields:
        if not f.value:
            f.confidence = 0.0
    return result


def extract_transport(
    data: bytes, content_type: str | None, filename: str | None
) -> ExtractionResult:
    """Adquiere texto (con OCR si aplica) y extrae los campos de transporte."""
    text, pages, method = acquire_text(data, content_type, filename, ocr_enabled=settings.ocr_enabled)
    result = extract_transport_from_text(text)
    base = OCR_MODEL_VERSION if method == "ocr" else TEXT_MODEL_VERSION
    result.model_version = base + (f"+pdf({pages}p)" if pages and pages > 1 else "")
    return result


# --------------------------------------------------------------------------- #
#  Extractores
# --------------------------------------------------------------------------- #
class HeuristicProformaExtractor:
    """Extractor SOLO texto (texto/CSV y PDFs con capa de texto). Determinista."""

    def extract(self, data: bytes, content_type: str | None, filename: str | None) -> ExtractionResult:
        text, pages, _ = acquire_text(data, content_type, filename, ocr_enabled=False)
        result = extract_fields_from_text(text)
        result.line_items = extract_line_items_from_text(text)
        result.model_version = TEXT_MODEL_VERSION + (f"+pdf({pages}p)" if pages else "")
        return result


class OcrExtractor:
    """Extractor OCR-capaz: capa de texto primero, OCR real (Tesseract) como respaldo."""

    def extract(self, data: bytes, content_type: str | None, filename: str | None) -> ExtractionResult:
        text, pages, method = acquire_text(data, content_type, filename, ocr_enabled=settings.ocr_enabled)
        result = extract_fields_from_text(text)
        result.line_items = extract_line_items_from_text(text)
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
