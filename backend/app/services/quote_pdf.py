"""Generación del PDF de la cotización (reportlab, puro Python).

Muestra la vista al cliente: NO incluye costo interno ni margen.
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.quote import Quote

DISCLAIMER = (
    "Los valores de tributos, aranceles, tasas, gastos logísticos y demás costos presentados "
    "constituyen una estimación basada en la información disponible y en la normativa configurada "
    "como vigente al momento del cálculo. La liquidación definitiva será la determinada por las "
    "autoridades y terceros correspondientes según la información y condiciones reales de la "
    "importación."
)

ACCENT = colors.HexColor("#0f6fc4")
LIGHT = colors.HexColor("#eef3f9")


def _money(cur: str, value) -> str:
    return f"{cur} {float(value or 0):,.2f}"


def build_quote_pdf(quote: Quote) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title=f"Cotización {quote.quote_number}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=18, textColor=ACCENT, spaceAfter=2)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    normal = styles["Normal"]
    cur = quote.currency

    elems = []
    elems.append(Paragraph("CAOP — Cotización de Importación", h1))
    elems.append(Paragraph(
        f"{quote.quote_number} · v{quote.version} · Estado: {quote.status}", small
    ))
    elems.append(Spacer(1, 8))

    meta = [
        ["Modalidad", quote.transport_mode or "-", "Incoterm", quote.incoterm or "-"],
        ["Tipo de carga", quote.load_type or "-", "Origen", quote.origin_country or "-"],
        ["Fecha cálculo", str(quote.calculation_date), "Válida hasta", str(quote.valid_until or "-")],
        ["Fecha estimada importación", str(quote.expected_import_date or "-"),
         "Confianza", f"{float(quote.confidence or 0):.0f}%"],
    ]
    t = Table(meta, colWidths=[42 * mm, 45 * mm, 40 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 10))

    # Ítems
    header = ["#", "Descripción", "HS", "Cant.", "Valor", "CIF", "Tributos"]
    rows = [header]
    for it in quote.items:
        rows.append([
            str(it.line_no),
            (it.description or "")[:38],
            it.hs_code or "-",
            f"{float(it.quantity or 0):,.0f}",
            _money(cur, it.line_value),
            _money(cur, it.cif_value),
            _money(cur, it.taxes_total),
        ])
    items_tbl = Table(rows, colWidths=[8 * mm, 55 * mm, 22 * mm, 16 * mm, 26 * mm, 26 * mm, 26 * mm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d8e0ea")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(items_tbl)
    elems.append(Spacer(1, 10))

    # Servicios / gastos cotizados (incluidos)
    included = [c for c in quote.cost_lines if c.is_included]
    if included:
        crows = [["Concepto", "Categoría", "Confianza", "Valor"]]
        for c in included:
            crows.append([
                (c.description or "")[:40], c.category, c.confidence, _money(cur, c.quoted_amount)
            ])
        ctbl = Table(crows, colWidths=[70 * mm, 30 * mm, 25 * mm, 30 * mm])
        ctbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d8e0ea")),
        ]))
        elems.append(Paragraph("Servicios y gastos cotizados", normal))
        elems.append(Spacer(1, 4))
        elems.append(ctbl)
        elems.append(Spacer(1, 10))

    # Resumen
    summary = [
        ["Valor mercancía (CIF)", _money(cur, quote.total_cif)],
        ["Tributos estimados", _money(cur, quote.total_taxes)],
        ["Servicios y gastos", _money(cur, quote.customer_price_total)],
        ["COSTO TOTAL ESTIMADO (LANDED)", _money(cur, quote.landed_cost_total)],
        ["Costo estimado por unidad", _money(cur, quote.landed_cost_per_unit)],
    ]
    stbl = Table(summary, colWidths=[95 * mm, 60 * mm])
    stbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, 3), (-1, 3), 0.8, ACCENT),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 3), (-1, 3), ACCENT),
    ]))
    elems.append(stbl)
    elems.append(Spacer(1, 8))

    # Exclusiones
    excluded = [c for c in quote.cost_lines if not c.is_included]
    if excluded:
        txt = "NO INCLUIDO / posibles costos adicionales: " + ", ".join(
            (c.description or c.category) for c in excluded
        )
        elems.append(Paragraph(txt, small))
        elems.append(Spacer(1, 6))

    elems.append(Spacer(1, 6))
    elems.append(Paragraph(DISCLAIMER, small))

    doc.build(elems)
    return buf.getvalue()
