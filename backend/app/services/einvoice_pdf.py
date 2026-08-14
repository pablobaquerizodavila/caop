"""RIDE — Representación Impresa del Documento Electrónico (factura SRI), en PDF."""

from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings
from app.models.einvoice import ElectronicInvoice
from app.models.settlement import Settlement

ACCENT = colors.HexColor("#0f6fc4")
LIGHT = colors.HexColor("#eef3f9")
CENT = Decimal("0.01")


def _money(v) -> str:
    return f"{float(v or 0):,.2f}"


def build_ride(inv: ElectronicInvoice, settlement: Settlement, customer_name: str,
               customer_id: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
        leftMargin=16 * mm, rightMargin=16 * mm, title=f"RIDE {inv.access_key}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=15, textColor=ACCENT, spaceAfter=2)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=7.5, textColor=colors.grey)
    normal = styles["Normal"]
    rate = Decimal(settlement.iva_rate or 0)

    elems = [
        Paragraph("FACTURA — Representación Impresa (RIDE)", h1),
        Paragraph(
            "SIMULADO · sin transmisión real al SRI" if inv.is_simulated
            else "Comprobante electrónico", small,
        ),
        Spacer(1, 8),
    ]

    emisor = [
        ["Razón social", settings.sri_razon_social],
        ["RUC", settings.sri_ruc],
        ["Ambiente", "Producción" if inv.ambiente == "2" else "Pruebas"],
        ["Comprobante", f"{inv.estab}-{inv.pto_emi}-{inv.secuencial}"],
        ["Fecha emisión", inv.issue_date.strftime("%d/%m/%Y")],
        ["Estado", inv.status],
    ]
    t = Table(emisor, colWidths=[40 * mm, 118 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 6))

    elems.append(Paragraph(f"<b>Clave de acceso:</b> {inv.access_key}", small))
    if inv.authorization_number:
        elems.append(Paragraph(f"<b>N.º autorización:</b> {inv.authorization_number}", small))
    elems.append(Spacer(1, 8))

    elems.append(Paragraph(f"Cliente: {customer_name} · ID: {customer_id}", normal))
    elems.append(Spacer(1, 8))

    rows = [["Descripción", "Cant.", "P. Unit.", "IVA", "Total"]]
    fees = [ln for ln in settlement.lines if ln.kind == "FEE"]
    for ln in fees:
        amt = Decimal(ln.amount or 0)
        iva = (amt * rate / 100).quantize(CENT) if ln.taxable else Decimal(0)
        rows.append([
            (ln.description or "Servicio")[:48], "1.00", _money(amt),
            _money(iva), _money(amt + iva),
        ])
    tbl = Table(rows, colWidths=[80 * mm, 16 * mm, 24 * mm, 20 * mm, 26 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d8e0ea")),
    ]))
    elems.append(tbl)
    elems.append(Spacer(1, 8))

    totals = [
        ["Subtotal", _money(inv.subtotal)],
        [f"IVA ({float(rate):.0f}%)", _money(inv.tax_amount)],
        ["IMPORTE TOTAL", _money(inv.total)],
    ]
    st = Table(totals, colWidths=[120 * mm, 46 * mm])
    st.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, 2), (-1, 2), 0.8, ACCENT),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 2), (-1, 2), ACCENT),
    ]))
    elems.append(st)
    elems.append(Spacer(1, 10))
    elems.append(Paragraph(
        "Documento generado por CAOP. La representación impresa no reemplaza al comprobante "
        "electrónico (XML) autorizado por el SRI.", small,
    ))

    doc.build(elems)
    return buf.getvalue()
