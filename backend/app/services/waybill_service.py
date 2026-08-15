"""Guía de remisión SRI: XML (guiaRemision) + orquestación."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.waybill import WaybillGuide, WaybillItem
from app.services.sri_connector import SriUnavailableError, get_sri_connector
from app.services.sri_service import SriError, build_access_key


def build_waybill_xml(g: WaybillGuide) -> str:
    def sub(parent, tag, text):
        e = SubElement(parent, tag)
        e.text = str(text)
        return e

    root = Element("guiaRemision", {"id": "comprobante", "version": "1.1.0"})

    it = SubElement(root, "infoTributaria")
    sub(it, "ambiente", g.ambiente)
    sub(it, "tipoEmision", g.emission_type)
    sub(it, "razonSocial", settings.sri_razon_social)
    sub(it, "nombreComercial", settings.sri_nombre_comercial)
    sub(it, "ruc", settings.sri_ruc)
    sub(it, "claveAcceso", g.access_key)
    sub(it, "codDoc", "06")
    sub(it, "estab", g.estab)
    sub(it, "ptoEmi", g.pto_emi)
    sub(it, "secuencial", g.secuencial)
    sub(it, "dirMatriz", settings.sri_dir_matriz)

    inf = SubElement(root, "infoGuiaRemision")
    sub(inf, "dirEstablecimiento", settings.sri_dir_establecimiento)
    sub(inf, "dirPartida", g.dir_partida)
    sub(inf, "razonSocialTransportista", g.transporter_name)
    sub(inf, "tipoIdentificacionTransportista", g.transporter_id_type)
    sub(inf, "rucTransportista", g.transporter_id)
    sub(inf, "obligadoContabilidad", settings.sri_obligado_contabilidad)
    sub(inf, "fechaIniTransporte", g.fecha_ini_transporte.strftime("%d/%m/%Y"))
    sub(inf, "fechaFinTransporte", g.fecha_fin_transporte.strftime("%d/%m/%Y"))
    sub(inf, "placa", g.placa)

    dests = SubElement(root, "destinatarios")
    d = SubElement(dests, "destinatario")
    sub(d, "identificacionDestinatario", g.dest_id)
    sub(d, "razonSocialDestinatario", g.dest_name)
    sub(d, "dirDestinatario", g.dest_address)
    sub(d, "motivoTraslado", g.motivo_traslado)
    if g.num_doc_sustento:
        sub(d, "codDocSustento", "01")
        sub(d, "numDocSustento", g.num_doc_sustento.replace("-", ""))
        if g.fecha_doc_sustento:
            sub(d, "fechaEmisionDocSustento", g.fecha_doc_sustento.strftime("%d/%m/%Y"))
    det = SubElement(d, "detalles")
    for item in g.items:
        de = SubElement(det, "detalle")
        sub(de, "codigoInterno", "ITEM")
        sub(de, "descripcion", item.description[:300])
        sub(de, "cantidad", f"{Decimal(item.quantity or 0):.2f}")

    ia = SubElement(root, "infoAdicional")
    ca = SubElement(ia, "campoAdicional", {"nombre": "placa"})
    ca.text = g.placa

    body = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


async def list_guides(session: AsyncSession, limit: int = 100) -> list[WaybillGuide]:
    return list(
        await session.scalars(
            select(WaybillGuide).order_by(WaybillGuide.created_at.desc()).limit(limit)
        )
    )


async def get_by_id(session: AsyncSession, g_id) -> WaybillGuide | None:
    return await session.scalar(select(WaybillGuide).where(WaybillGuide.id == g_id))


async def _next_secuencial(session: AsyncSession, estab: str, pto_emi: str) -> str:
    last = await session.scalar(
        select(func.max(WaybillGuide.secuencial)).where(
            WaybillGuide.estab == estab, WaybillGuide.pto_emi == pto_emi
        )
    )
    return f"{(int(last) + 1) if last else 1:09d}"


async def create(session: AsyncSession, data: dict, items: list[dict]) -> WaybillGuide:
    if not items:
        raise SriError("La guía de remisión requiere al menos un ítem.")

    estab, pto_emi = settings.sri_estab, settings.sri_pto_emi
    ambiente = settings.sri_ambiente
    secuencial = await _next_secuencial(session, estab, pto_emi)
    issue = date.today()
    access_key = build_access_key(issue, "06", settings.sri_ruc, ambiente, estab, pto_emi, secuencial, "1")

    g = WaybillGuide(
        ambiente=ambiente, emission_type="1", estab=estab, pto_emi=pto_emi,
        secuencial=secuencial, access_key=access_key, issue_date=issue, status="DRAFT",
        is_simulated=get_sri_connector().is_simulator, **data,
    )
    for it in items:
        g.items.append(WaybillItem(
            description=it["description"], quantity=Decimal(str(it.get("quantity", 1))),
        ))
    session.add(g)
    await session.flush()
    g.xml = build_waybill_xml(g)
    await session.flush()
    return await get_by_id(session, g.id)


async def authorize(session: AsyncSession, g: WaybillGuide, scenario: str = "AUTHORIZE") -> WaybillGuide:
    conn = get_sri_connector()
    g.xml = conn.sign(g.xml or "")
    g.signed = True
    if g.status == "DRAFT":
        g.status = "SIGNED"
    try:
        result = conn.authorize(g.access_key, g.xml, scenario)
    except SriUnavailableError as exc:
        g.error = str(exc)
        return g
    if result.estado == "AUTHORIZED":
        g.status = "AUTHORIZED"
        g.authorization_number = result.authorization_number
        g.authorized_at = datetime.now(timezone.utc)
        g.error = None
    else:
        g.status = "REJECTED"
        g.error = result.message
    await session.flush()
    return g
