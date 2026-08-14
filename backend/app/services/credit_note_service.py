"""Nota de crédito SRI: XML (notaCredito) + orquestación, sobre una factura autorizada."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.credit_note import CreditNote
from app.models.customer import Customer
from app.models.einvoice import ElectronicInvoice
from app.models.settlement import Settlement
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.services.sri_connector import SriUnavailableError, get_sri_connector
from app.services.sri_service import CENT, SriError, build_access_key, iva_codigo_porcentaje


def _money(v) -> str:
    return f"{Decimal(v or 0).quantize(CENT)}"


def build_credit_note_xml(
    cn: CreditNote, num_doc_modificado: str, fecha_sustento: date,
    customer: Customer | None, rate: Decimal,
) -> str:
    def sub(parent, tag, text):
        e = SubElement(parent, tag)
        e.text = str(text)
        return e

    base = Decimal(cn.subtotal or 0)
    iva = Decimal(cn.tax_amount or 0)
    cod_pct = iva_codigo_porcentaje(rate) if iva > 0 else "0"

    root = Element("notaCredito", {"id": "comprobante", "version": "1.1.0"})

    it = SubElement(root, "infoTributaria")
    sub(it, "ambiente", cn.ambiente)
    sub(it, "tipoEmision", cn.emission_type)
    sub(it, "razonSocial", settings.sri_razon_social)
    sub(it, "nombreComercial", settings.sri_nombre_comercial)
    sub(it, "ruc", settings.sri_ruc)
    sub(it, "claveAcceso", cn.access_key)
    sub(it, "codDoc", "04")
    sub(it, "estab", cn.estab)
    sub(it, "ptoEmi", cn.pto_emi)
    sub(it, "secuencial", cn.secuencial)
    sub(it, "dirMatriz", settings.sri_dir_matriz)

    inf = SubElement(root, "infoNotaCredito")
    sub(inf, "fechaEmision", cn.issue_date.strftime("%d/%m/%Y"))
    sub(inf, "dirEstablecimiento", settings.sri_dir_establecimiento)
    cust_ruc = customer.ruc if customer and customer.ruc else "9999999999999"
    sub(inf, "tipoIdentificacionComprador", "04" if len(cust_ruc) == 13 else "05")
    sub(inf, "razonSocialComprador", customer.legal_name if customer else "CONSUMIDOR FINAL")
    sub(inf, "identificacionComprador", cust_ruc)
    sub(inf, "obligadoContabilidad", settings.sri_obligado_contabilidad)
    sub(inf, "codDocModificado", "01")
    sub(inf, "numDocModificado", num_doc_modificado)
    sub(inf, "fechaEmisionDocSustento", fecha_sustento.strftime("%d/%m/%Y"))
    sub(inf, "totalSinImpuestos", _money(base))
    sub(inf, "valorModificacion", _money(cn.total))
    sub(inf, "moneda", "DOLAR")
    tci = SubElement(inf, "totalConImpuestos")
    ti = SubElement(tci, "totalImpuesto")
    sub(ti, "codigo", "2")
    sub(ti, "codigoPorcentaje", cod_pct)
    sub(ti, "baseImponible", _money(base))
    sub(ti, "valor", _money(iva))
    sub(inf, "motivo", cn.motivo[:300])

    det = SubElement(root, "detalles")
    d = SubElement(det, "detalle")
    sub(d, "codigoInterno", "NC-001")
    sub(d, "descripcion", (cn.motivo or "Nota de crédito")[:300])
    sub(d, "cantidad", "1.00")
    sub(d, "precioUnitario", _money(base))
    sub(d, "descuento", "0.00")
    sub(d, "precioTotalSinImpuesto", _money(base))
    imps = SubElement(d, "impuestos")
    imp = SubElement(imps, "impuesto")
    sub(imp, "codigo", "2")
    sub(imp, "codigoPorcentaje", cod_pct)
    sub(imp, "tarifa", f"{rate:.0f}" if iva > 0 else "0")
    sub(imp, "baseImponible", _money(base))
    sub(imp, "valor", _money(iva))

    ia = SubElement(root, "infoAdicional")
    ca = SubElement(ia, "campoAdicional", {"nombre": "facturaModificada"})
    ca.text = num_doc_modificado

    body = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


async def list_for_invoice(session: AsyncSession, invoice_id) -> list[CreditNote]:
    return list(
        await session.scalars(
            select(CreditNote).where(CreditNote.invoice_id == invoice_id)
            .order_by(CreditNote.created_at)
        )
    )


async def _next_secuencial(session: AsyncSession, estab: str, pto_emi: str) -> str:
    last = await session.scalar(
        select(func.max(CreditNote.secuencial)).where(
            CreditNote.estab == estab, CreditNote.pto_emi == pto_emi
        )
    )
    return f"{(int(last) + 1) if last else 1:09d}"


async def create_from_invoice(
    session: AsyncSession, invoice: ElectronicInvoice, amount: Decimal | None, motivo: str,
) -> CreditNote:
    if invoice.status != "AUTHORIZED":
        raise SriError("Solo se puede emitir nota de crédito sobre una factura autorizada.")

    inv_total = Decimal(invoice.total or 0)
    total = Decimal(amount) if amount is not None else inv_total
    if total <= 0 or total > inv_total:
        raise SriError("El monto de la nota de crédito debe ser mayor a 0 y no exceder la factura.")

    settlement = await session.get(Settlement, invoice.settlement_id)
    rate = Decimal(settlement.iva_rate or 0) if settlement else Decimal(0)

    if total == inv_total:  # crédito total: refleja exactamente la factura
        base = Decimal(invoice.subtotal or 0)
        iva = Decimal(invoice.tax_amount or 0)
    else:  # crédito parcial: se separa la base y el IVA a la tarifa vigente
        base = (total / (1 + rate / 100)).quantize(CENT)
        iva = (total - base).quantize(CENT)

    estab, pto_emi = settings.sri_estab, settings.sri_pto_emi
    ambiente = settings.sri_ambiente
    secuencial = await _next_secuencial(session, estab, pto_emi)
    issue = date.today()
    access_key = build_access_key(issue, "04", settings.sri_ruc, ambiente, estab, pto_emi, secuencial, "1")

    customer = None
    if invoice.customs_case_id:
        case = await session.get(CustomsCase, invoice.customs_case_id)
        if case:
            shipment = await session.get(Shipment, case.shipment_id)
            if shipment:
                customer = await session.get(Customer, shipment.customer_id)

    cn = CreditNote(
        invoice_id=invoice.id, customs_case_id=invoice.customs_case_id,
        ambiente=ambiente, emission_type="1", estab=estab, pto_emi=pto_emi,
        secuencial=secuencial, access_key=access_key, issue_date=issue, status="DRAFT",
        is_simulated=get_sri_connector().is_simulator, motivo=motivo or "Corrección",
        subtotal=base, tax_amount=iva, total=total.quantize(CENT),
    )
    num_doc = f"{invoice.estab}-{invoice.pto_emi}-{invoice.secuencial}"
    cn.xml = build_credit_note_xml(cn, num_doc, invoice.issue_date, customer, rate)
    session.add(cn)
    if invoice.customs_case_id:
        session.add(CaseEvent(
            customs_case_id=invoice.customs_case_id, event_type="CREDIT_NOTE_CREATED",
            event_source="SYSTEM",
            normalized_payload={"access_key": access_key, "modifica": num_doc},
        ))
    await session.flush()
    return cn


async def authorize(session: AsyncSession, cn: CreditNote, scenario: str = "AUTHORIZE") -> CreditNote:
    conn = get_sri_connector()
    cn.xml = conn.sign(cn.xml or "")
    cn.signed = True
    if cn.status == "DRAFT":
        cn.status = "SIGNED"
    try:
        result = conn.authorize(cn.access_key, cn.xml, scenario)
    except SriUnavailableError as exc:
        cn.error = str(exc)
        return cn
    if result.estado == "AUTHORIZED":
        cn.status = "AUTHORIZED"
        cn.authorization_number = result.authorization_number
        cn.authorized_at = datetime.now(timezone.utc)
        cn.error = None
        event = "CREDIT_NOTE_AUTHORIZED"
    else:
        cn.status = "REJECTED"
        cn.error = result.message
        event = "CREDIT_NOTE_REJECTED"
    if cn.customs_case_id:
        session.add(CaseEvent(
            customs_case_id=cn.customs_case_id, event_type=event, event_source="SYSTEM",
            normalized_payload={"access_key": cn.access_key},
        ))
    await session.flush()
    return cn
