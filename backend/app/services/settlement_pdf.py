"""PDF de la liquidación al cliente (reportlab)."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.settlement import Settlement

ACCENT = colors.HexColor("#0f6fc4")
LIGHT = colors.HexColor("#eef3f9")

DISCLAIMER = (
    "Liquidación de gastos del servicio de agenciamiento aduanero. Los desembolsos "
    "reembolsables (tributos, flete, seguro, almacenaje, demurrage y otros) se trasladan al "
    "cliente al valor efectivamente incurrido; los montos estimados se ajustarán a la "
    "liquidación real de las autoridades y terceros. Este documento no constituye un "
    "comprobante de venta electrónico autorizado por el SRI."
)

_CAT_LABEL = {
    "HONORARIO": "Honorarios", "TRIBUTO": "Tributos aduaneros", "FLETE": "Flete",
    "SEGURO": "Seguro", "ALMACENAJE": "Almacenaje", "DEMURRAGE": "Demurrage",
    "PORTUARIO": "Gastos portuarios", "TRANSPORTE": "Transporte interno", "OTRO": "Otros",
}


def _money(cur: str, value) -> str:
    return f"{cur} {float(value or 0):,.2f}"


def build_settlement_pdf(stl: Settlement, case_number: str, customer_name: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title=f"Liquidación {stl.settlement_number}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=18, textColor=ACCENT, spaceAfter=2)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    cur = stl.currency

    elems = [
        Paragraph("CAOP — Liquidación de gastos", h1),
        Paragraph(
            f"{stl.settlement_number} · Expediente {case_number} · Estado: {stl.status}", small
        ),
        Paragraph(f"Cliente: {customer_name}", small),
        Spacer(1, 10),
    ]

    def section(title: str, kind: str) -> None:
        rows = [["Concepto", "Categoría", "Monto"]]
        lines = [ln for ln in stl.lines if ln.kind == kind]
        if not lines:
            return
        for ln in lines:
            rows.append([
                (ln.description or "")[:52],
                _CAT_LABEL.get(ln.category, ln.category),
                _money(cur, ln.amount),
            ])
        tbl = Table(rows, colWidths=[95 * mm, 35 * mm, 30 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d8e0ea")),
        ]))
        elems.append(Paragraph(title, styles["Normal"]))
        elems.append(Spacer(1, 4))
        elems.append(tbl)
        elems.append(Spacer(1, 10))

    section("Honorarios (servicio)", "FEE")
    section("Desembolsos reembolsables", "DISBURSEMENT")

    summary = [
        ["Subtotal honorarios", _money(cur, stl.subtotal_fees)],
        [f"IVA ({float(stl.iva_rate):.0f}%) sobre honorarios", _money(cur, stl.tax_amount)],
        ["Desembolsos reembolsables", _money(cur, stl.subtotal_disbursements)],
        ["TOTAL A PAGAR", _money(cur, stl.total)],
    ]
    stbl = Table(summary, colWidths=[95 * mm, 60 * mm])
    stbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, 3), (-1, 3), 0.8, ACCENT),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 3), (-1, 3), ACCENT),
    ]))
    elems.append(stbl)
    elems.append(Spacer(1, 10))
    if stl.notes:
        elems.append(Paragraph(stl.notes, small))
        elems.append(Spacer(1, 6))
    elems.append(Paragraph(DISCLAIMER, small))

    doc.build(elems)
    return buf.getvalue()
