"""Nota de débito SRI: XML (notaDebito) + orquestación, sobre una factura autorizada."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer
from app.models.debit_note import DebitNote
from app.models.einvoice import ElectronicInvoice
from app.models.settlement import Settlement
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.services.sri_connector import SriUnavailableError, get_sri_connector
from app.services.sri_service import CENT, SriError, build_access_key, iva_codigo_porcentaje


def _money(v) -> str:
    return f"{Decimal(v or 0).quantize(CENT)}"


def build_debit_note_xml(
    dn: DebitNote, num_doc_modificado: str, fecha_sustento: date,
    customer: Customer | None, rate: Decimal,
) -> str:
    def sub(parent, tag, text):
        e = SubElement(parent, tag)
        e.text = str(text)
        return e

    base = Decimal(dn.subtotal or 0)
    iva = Decimal(dn.tax_amount or 0)
    cod_pct = iva_codigo_porcentaje(rate) if iva > 0 else "0"

    root = Element("notaDebito", {"id": "comprobante", "version": "1.0.0"})

    it = SubElement(root, "infoTributaria")
    sub(it, "ambiente", dn.ambiente)
    sub(it, "tipoEmision", dn.emission_type)
    sub(it, "razonSocial", settings.sri_razon_social)
    sub(it, "nombreComercial", settings.sri_nombre_comercial)
    sub(it, "ruc", settings.sri_ruc)
    sub(it, "claveAcceso", dn.access_key)
    sub(it, "codDoc", "05")
    sub(it, "estab", dn.estab)
    sub(it, "ptoEmi", dn.pto_emi)
    sub(it, "secuencial", dn.secuencial)
    sub(it, "dirMatriz", settings.sri_dir_matriz)

    inf = SubElement(root, "infoNotaDebito")
    sub(inf, "fechaEmision", dn.issue_date.strftime("%d/%m/%Y"))
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

    imps = SubElement(inf, "impuestos")
    imp = SubElement(imps, "impuesto")
    sub(imp, "codigo", "2")
    sub(imp, "codigoPorcentaje", cod_pct)
    sub(imp, "tarifa", f"{rate:.0f}" if iva > 0 else "0")
    sub(imp, "baseImponible", _money(base))
    sub(imp, "valor", _money(iva))

    sub(inf, "valorTotal", _money(dn.total))
    motivos = SubElement(inf, "motivos")
    motivo = SubElement(motivos, "motivo")
    sub(motivo, "razon", (dn.motivo or "Cargo adicional")[:300])
    sub(motivo, "valor", _money(dn.total))

    ia = SubElement(root, "infoAdicional")
    ca = SubElement(ia, "campoAdicional", {"nombre": "facturaModificada"})
    ca.text = num_doc_modificado

    body = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


async def list_for_invoice(session: AsyncSession, invoice_id) -> list[DebitNote]:
    return list(
        await session.scalars(
            select(DebitNote).where(DebitNote.invoice_id == invoice_id)
            .order_by(DebitNote.created_at)
        )
    )


async def _next_secuencial(session: AsyncSession, estab: str, pto_emi: str) -> str:
    last = await session.scalar(
        select(func.max(DebitNote.secuencial)).where(
            DebitNote.estab == estab, DebitNote.pto_emi == pto_emi
        )
    )
    return f"{(int(last) + 1) if last else 1:09d}"


async def create_from_invoice(
    session: AsyncSession, invoice: ElectronicInvoice, amount: Decimal, motivo: str,
) -> DebitNote:
    if invoice.status != "AUTHORIZED":
        raise SriError("Solo se puede emitir nota de débito sobre una factura autorizada.")
    total = Decimal(amount)
    if total <= 0:
        raise SriError("El monto de la nota de débito debe ser mayor a 0.")

    settlement = await session.get(Settlement, invoice.settlement_id)
    rate = Decimal(settlement.iva_rate or 0) if settlement else Decimal(0)
    base = (total / (1 + rate / 100)).quantize(CENT)
    iva = (total - base).quantize(CENT)

    estab, pto_emi = settings.sri_estab, settings.sri_pto_emi
    ambiente = settings.sri_ambiente
    secuencial = await _next_secuencial(session, estab, pto_emi)
    issue = date.today()
    access_key = build_access_key(issue, "05", settings.sri_ruc, ambiente, estab, pto_emi, secuencial, "1")

    customer = None
    if invoice.customs_case_id:
        case = await session.get(CustomsCase, invoice.customs_case_id)
        if case:
            shipment = await session.get(Shipment, case.shipment_id)
            if shipment:
                customer = await session.get(Customer, shipment.customer_id)

    dn = DebitNote(
        invoice_id=invoice.id, customs_case_id=invoice.customs_case_id,
        ambiente=ambiente, emission_type="1", estab=estab, pto_emi=pto_emi,
        secuencial=secuencial, access_key=access_key, issue_date=issue, status="DRAFT",
        is_simulated=get_sri_connector().is_simulator, motivo=motivo or "Cargo adicional",
        subtotal=base, tax_amount=iva, total=total.quantize(CENT),
    )
    num_doc = f"{invoice.estab}-{invoice.pto_emi}-{invoice.secuencial}"
    dn.xml = build_debit_note_xml(dn, num_doc, invoice.issue_date, customer, rate)
    session.add(dn)
    if invoice.customs_case_id:
        session.add(CaseEvent(
            customs_case_id=invoice.customs_case_id, event_type="DEBIT_NOTE_CREATED",
            event_source="SYSTEM",
            normalized_payload={"access_key": access_key, "modifica": num_doc},
        ))
    await session.flush()
    return dn


async def authorize(session: AsyncSession, dn: DebitNote, scenario: str = "AUTHORIZE") -> DebitNote:
    conn = get_sri_connector()
    dn.xml = conn.sign(dn.xml or "")
    dn.signed = True
    if dn.status == "DRAFT":
        dn.status = "SIGNED"
    try:
        result = conn.authorize(dn.access_key, dn.xml, scenario)
    except SriUnavailableError as exc:
        dn.error = str(exc)
        return dn
    if result.estado == "AUTHORIZED":
        dn.status = "AUTHORIZED"
        dn.authorization_number = result.authorization_number
        dn.authorized_at = datetime.now(timezone.utc)
        dn.error = None
        event = "DEBIT_NOTE_AUTHORIZED"
    else:
        dn.status = "REJECTED"
        dn.error = result.message
        event = "DEBIT_NOTE_REJECTED"
    if dn.customs_case_id:
        session.add(CaseEvent(
            customs_case_id=dn.customs_case_id, event_type=event, event_source="SYSTEM",
            normalized_payload={"access_key": dn.access_key},
        ))
    await session.flush()
    return dn
