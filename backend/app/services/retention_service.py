"""Comprobante de retención SRI: XML (comprobanteRetencion) + orquestación."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.retention import RetentionLine, RetentionVoucher
from app.services.sri_connector import SriUnavailableError, get_sri_connector
from app.services.sri_service import CENT, SriError, build_access_key


def _money(v) -> str:
    return f"{Decimal(v or 0).quantize(CENT)}"


def build_retention_xml(rv: RetentionVoucher) -> str:
    def sub(parent, tag, text):
        e = SubElement(parent, tag)
        e.text = str(text)
        return e

    root = Element("comprobanteRetencion", {"id": "comprobante", "version": "1.0.0"})

    it = SubElement(root, "infoTributaria")
    sub(it, "ambiente", rv.ambiente)
    sub(it, "tipoEmision", rv.emission_type)
    sub(it, "razonSocial", settings.sri_razon_social)
    sub(it, "nombreComercial", settings.sri_nombre_comercial)
    sub(it, "ruc", settings.sri_ruc)
    sub(it, "claveAcceso", rv.access_key)
    sub(it, "codDoc", "07")
    sub(it, "estab", rv.estab)
    sub(it, "ptoEmi", rv.pto_emi)
    sub(it, "secuencial", rv.secuencial)
    sub(it, "dirMatriz", settings.sri_dir_matriz)

    inf = SubElement(root, "infoCompRetencion")
    sub(inf, "fechaEmision", rv.issue_date.strftime("%d/%m/%Y"))
    sub(inf, "dirEstablecimiento", settings.sri_dir_establecimiento)
    sub(inf, "obligadoContabilidad", settings.sri_obligado_contabilidad)
    sub(inf, "tipoIdentificacionSujetoRetenido", rv.subject_id_type)
    sub(inf, "razonSocialSujetoRetenido", rv.subject_name)
    sub(inf, "identificacionSujetoRetenido", rv.subject_id)
    sub(inf, "periodoFiscal", rv.period)

    imps = SubElement(root, "impuestos")
    for ln in rv.lines:
        imp = SubElement(imps, "impuesto")
        sub(imp, "codigo", ln.tax_type)
        sub(imp, "codigoRetencion", ln.codigo_retencion)
        sub(imp, "baseImponible", _money(ln.base_imponible))
        sub(imp, "porcentajeRetener", _money(ln.percentage))
        sub(imp, "valorRetenido", _money(ln.value))
        sub(imp, "codDocSustento", rv.doc_sustento_type)
        sub(imp, "numDocSustento", rv.doc_sustento_number.replace("-", ""))
        sub(imp, "fechaEmisionDocSustento", rv.doc_sustento_date.strftime("%d/%m/%Y"))

    ia = SubElement(root, "infoAdicional")
    ca = SubElement(ia, "campoAdicional", {"nombre": "docSustento"})
    ca.text = rv.doc_sustento_number

    body = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


async def list_vouchers(session: AsyncSession, limit: int = 100) -> list[RetentionVoucher]:
    return list(
        await session.scalars(
            select(RetentionVoucher).order_by(RetentionVoucher.created_at.desc()).limit(limit)
        )
    )


async def get_by_id(session: AsyncSession, rv_id) -> RetentionVoucher | None:
    return await session.scalar(select(RetentionVoucher).where(RetentionVoucher.id == rv_id))


async def _next_secuencial(session: AsyncSession, estab: str, pto_emi: str) -> str:
    last = await session.scalar(
        select(func.max(RetentionVoucher.secuencial)).where(
            RetentionVoucher.estab == estab, RetentionVoucher.pto_emi == pto_emi
        )
    )
    return f"{(int(last) + 1) if last else 1:09d}"


async def create(session: AsyncSession, data: dict, lines: list[dict]) -> RetentionVoucher:
    if not lines:
        raise SriError("La retención requiere al menos una línea (Renta o IVA).")

    estab, pto_emi = settings.sri_estab, settings.sri_pto_emi
    ambiente = settings.sri_ambiente
    secuencial = await _next_secuencial(session, estab, pto_emi)
    issue = date.today()
    access_key = build_access_key(issue, "07", settings.sri_ruc, ambiente, estab, pto_emi, secuencial, "1")

    rv = RetentionVoucher(
        ambiente=ambiente, emission_type="1", estab=estab, pto_emi=pto_emi,
        secuencial=secuencial, access_key=access_key, issue_date=issue, status="DRAFT",
        is_simulated=get_sri_connector().is_simulator, **data,
    )
    total = Decimal(0)
    for ln in lines:
        base = Decimal(str(ln["base_imponible"]))
        pct = Decimal(str(ln["percentage"]))
        value = (base * pct / 100).quantize(CENT)
        total += value
        rv.lines.append(RetentionLine(
            tax_type=ln["tax_type"], codigo_retencion=ln["codigo_retencion"],
            base_imponible=base.quantize(CENT), percentage=pct, value=value,
        ))
    rv.total_retained = total.quantize(CENT)
    session.add(rv)
    await session.flush()
    rv.xml = build_retention_xml(rv)
    await session.flush()
    return await get_by_id(session, rv.id)


async def authorize(session: AsyncSession, rv: RetentionVoucher, scenario: str = "AUTHORIZE") -> RetentionVoucher:
    conn = get_sri_connector()
    rv.xml = conn.sign(rv.xml or "")
    rv.signed = True
    if rv.status == "DRAFT":
        rv.status = "SIGNED"
    try:
        result = conn.authorize(rv.access_key, rv.xml, scenario)
    except SriUnavailableError as exc:
        rv.error = str(exc)
        return rv
    if result.estado == "AUTHORIZED":
        rv.status = "AUTHORIZED"
        rv.authorization_number = result.authorization_number
        rv.authorized_at = datetime.now(timezone.utc)
        rv.error = None
    else:
        rv.status = "REJECTED"
        rv.error = result.message
    await session.flush()
    return rv
