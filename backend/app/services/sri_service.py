"""Facturación electrónica SRI: clave de acceso, XML de factura y orquestación.

Se genera el comprobante contra la estructura oficial del SRI con clave de acceso
válida (módulo 11). La firma XAdES-BES y la autorización pasan por un conector
enchufable (hoy SIMULADOR): NO hay transmisión real al SRI hasta conectar el .p12.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer
from app.models.einvoice import ElectronicInvoice
from app.models.settlement import Settlement
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.services.sri_connector import SriUnavailableError, get_sri_connector

CENT = Decimal("0.01")
_IVA_CODE = {0: "0", 5: "5", 8: "8", 12: "2", 14: "3", 15: "4"}


class SriError(ValueError):
    pass


def iva_codigo_porcentaje(rate: Decimal) -> str:
    return _IVA_CODE.get(int(rate), "4")


def _mod11(digits: str) -> int:
    weights = [2, 3, 4, 5, 6, 7]
    total = 0
    for i, ch in enumerate(reversed(digits)):
        total += int(ch) * weights[i % 6]
    r = 11 - (total % 11)
    return 0 if r == 11 else (1 if r == 10 else r)


def build_access_key(
    issue: date, cod_doc: str, ruc: str, ambiente: str, estab: str, pto_emi: str,
    secuencial: str, emission_type: str,
) -> str:
    """Clave de acceso de 49 dígitos (48 + dígito verificador módulo 11)."""
    serie = f"{estab}{pto_emi}"
    cod_num = f"{int(secuencial) % 100_000_000:08d}"
    key48 = (
        f"{issue.strftime('%d%m%Y')}{cod_doc}{ruc}{ambiente}{serie}"
        f"{secuencial}{cod_num}{emission_type}"
    )
    if len(key48) != 48:
        raise SriError(f"Clave de acceso inválida (len={len(key48)}); revise RUC/serie/secuencial.")
    return key48 + str(_mod11(key48))


def _money(v) -> str:
    return f"{Decimal(v or 0).quantize(CENT)}"


def build_factura_xml(
    settlement: Settlement, customer: Customer | None, *,
    ambiente: str, emission_type: str, estab: str, pto_emi: str, secuencial: str,
    access_key: str, issue: date,
) -> str:
    fees = [ln for ln in settlement.lines if ln.kind == "FEE"]
    if not fees:
        raise SriError("La factura requiere al menos un honorario/servicio gravable.")
    rate = Decimal(settlement.iva_rate or 0)
    cod_pct = iva_codigo_porcentaje(rate)

    base_total = sum((Decimal(ln.amount or 0) for ln in fees), Decimal(0))
    taxable_base = sum((Decimal(ln.amount or 0) for ln in fees if ln.taxable), Decimal(0))
    zero_base = base_total - taxable_base
    iva_val = (taxable_base * rate / 100).quantize(CENT)
    importe_total = (base_total + iva_val).quantize(CENT)

    def sub(parent, tag, text):
        e = SubElement(parent, tag)
        e.text = str(text)
        return e

    root = Element("factura", {"id": "comprobante", "version": "1.1.0"})

    it = SubElement(root, "infoTributaria")
    sub(it, "ambiente", ambiente)
    sub(it, "tipoEmision", emission_type)
    sub(it, "razonSocial", settings.sri_razon_social)
    sub(it, "nombreComercial", settings.sri_nombre_comercial)
    sub(it, "ruc", settings.sri_ruc)
    sub(it, "claveAcceso", access_key)
    sub(it, "codDoc", "01")
    sub(it, "estab", estab)
    sub(it, "ptoEmi", pto_emi)
    sub(it, "secuencial", secuencial)
    sub(it, "dirMatriz", settings.sri_dir_matriz)

    inf = SubElement(root, "infoFactura")
    sub(inf, "fechaEmision", issue.strftime("%d/%m/%Y"))
    sub(inf, "dirEstablecimiento", settings.sri_dir_establecimiento)
    sub(inf, "obligadoContabilidad", settings.sri_obligado_contabilidad)
    cust_ruc = customer.ruc if customer and customer.ruc else "9999999999999"
    sub(inf, "tipoIdentificacionComprador", "04" if len(cust_ruc) == 13 else "05")
    sub(inf, "razonSocialComprador", customer.legal_name if customer else "CONSUMIDOR FINAL")
    sub(inf, "identificacionComprador", cust_ruc)
    sub(inf, "totalSinImpuestos", _money(base_total))
    sub(inf, "totalDescuento", "0.00")

    tci = SubElement(inf, "totalConImpuestos")
    if taxable_base > 0:
        ti = SubElement(tci, "totalImpuesto")
        sub(ti, "codigo", "2"); sub(ti, "codigoPorcentaje", cod_pct)
        sub(ti, "baseImponible", _money(taxable_base)); sub(ti, "valor", _money(iva_val))
    if zero_base > 0 or taxable_base == 0:
        ti = SubElement(tci, "totalImpuesto")
        sub(ti, "codigo", "2"); sub(ti, "codigoPorcentaje", "0")
        sub(ti, "baseImponible", _money(zero_base)); sub(ti, "valor", "0.00")

    sub(inf, "propina", "0.00")
    sub(inf, "importeTotal", _money(importe_total))
    sub(inf, "moneda", "DOLAR")
    pagos = SubElement(inf, "pagos")
    pago = SubElement(pagos, "pago")
    sub(pago, "formaPago", "01")
    sub(pago, "total", _money(importe_total))

    det = SubElement(root, "detalles")
    for i, ln in enumerate(fees, start=1):
        amt = Decimal(ln.amount or 0)
        d = SubElement(det, "detalle")
        sub(d, "codigoPrincipal", f"SRV-{i:03d}")
        sub(d, "descripcion", (ln.description or "Servicio de agenciamiento")[:300])
        sub(d, "cantidad", "1.00")
        sub(d, "precioUnitario", _money(amt))
        sub(d, "descuento", "0.00")
        sub(d, "precioTotalSinImpuesto", _money(amt))
        imps = SubElement(d, "impuestos")
        imp = SubElement(imps, "impuesto")
        sub(imp, "codigo", "2")
        sub(imp, "codigoPorcentaje", cod_pct if ln.taxable else "0")
        sub(imp, "tarifa", f"{rate:.0f}" if ln.taxable else "0")
        sub(imp, "baseImponible", _money(amt))
        sub(imp, "valor", _money((amt * rate / 100).quantize(CENT)) if ln.taxable else "0.00")

    disb = sum(
        (Decimal(ln.amount or 0) for ln in settlement.lines if ln.kind == "DISBURSEMENT"),
        Decimal(0),
    )
    ia = SubElement(root, "infoAdicional")
    ca = SubElement(ia, "campoAdicional", {"nombre": "liquidacion"})
    ca.text = settlement.settlement_number
    if disb > 0:
        cd = SubElement(ia, "campoAdicional", {"nombre": "desembolsosReembolsables"})
        cd.text = _money(disb)

    body = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


async def get_for_settlement(session: AsyncSession, settlement_id) -> ElectronicInvoice | None:
    return await session.scalar(
        select(ElectronicInvoice).where(ElectronicInvoice.settlement_id == settlement_id)
    )


async def _next_secuencial(session: AsyncSession, estab: str, pto_emi: str) -> str:
    last = await session.scalar(
        select(func.max(ElectronicInvoice.secuencial)).where(
            ElectronicInvoice.estab == estab, ElectronicInvoice.pto_emi == pto_emi
        )
    )
    seq = (int(last) + 1) if last else 1
    return f"{seq:09d}"


async def create_from_settlement(session: AsyncSession, settlement: Settlement) -> ElectronicInvoice:
    if settlement.status != "ISSUED":
        raise SriError("La liquidación debe estar emitida antes de facturar.")
    existing = await get_for_settlement(session, settlement.id)
    if existing is not None:
        return existing

    case = await session.get(CustomsCase, settlement.customs_case_id)
    customer = None
    if case:
        shipment = await session.get(Shipment, case.shipment_id)
        if shipment:
            customer = await session.get(Customer, shipment.customer_id)

    estab, pto_emi = settings.sri_estab, settings.sri_pto_emi
    ambiente, emission_type = settings.sri_ambiente, "1"
    secuencial = await _next_secuencial(session, estab, pto_emi)
    issue = date.today()
    access_key = build_access_key(
        issue, "01", settings.sri_ruc, ambiente, estab, pto_emi, secuencial, emission_type
    )
    xml = build_factura_xml(
        settlement, customer, ambiente=ambiente, emission_type=emission_type, estab=estab,
        pto_emi=pto_emi, secuencial=secuencial, access_key=access_key, issue=issue,
    )
    inv = ElectronicInvoice(
        settlement_id=settlement.id, customs_case_id=settlement.customs_case_id,
        ambiente=ambiente, emission_type=emission_type, estab=estab, pto_emi=pto_emi,
        secuencial=secuencial, access_key=access_key, issue_date=issue, status="DRAFT",
        is_simulated=get_sri_connector().is_simulator,
        subtotal=settlement.subtotal_fees, tax_amount=settlement.tax_amount,
        total=(Decimal(settlement.subtotal_fees or 0) + Decimal(settlement.tax_amount or 0)),
        xml=xml,
    )
    session.add(inv)
    if case:
        session.add(CaseEvent(
            customs_case_id=case.id, event_type="EINVOICE_CREATED", event_source="SYSTEM",
            normalized_payload={"access_key": access_key, "secuencial": secuencial},
        ))
    await session.flush()
    return inv


async def authorize(session: AsyncSession, inv: ElectronicInvoice, scenario: str = "AUTHORIZE") -> ElectronicInvoice:
    conn = get_sri_connector()
    inv.xml = conn.sign(inv.xml or "")
    inv.signed = True
    if inv.status == "DRAFT":
        inv.status = "SIGNED"

    try:
        result = conn.authorize(inv.access_key, inv.xml, scenario)
    except SriUnavailableError as exc:
        inv.error = str(exc)
        return inv  # sigue SIGNED -> reintentable

    if result.estado == "AUTHORIZED":
        inv.status = "AUTHORIZED"
        inv.authorization_number = result.authorization_number
        inv.authorized_at = datetime.now(timezone.utc)
        inv.error = None
        event = "EINVOICE_AUTHORIZED"
    else:
        inv.status = "REJECTED"
        inv.error = result.message
        event = "EINVOICE_REJECTED"
    if inv.customs_case_id:
        session.add(CaseEvent(
            customs_case_id=inv.customs_case_id, event_type=event, event_source="SYSTEM",
            normalized_payload={"access_key": inv.access_key, "simulated": inv.is_simulated},
        ))
    await session.flush()
    return inv
