"""Semilla de catálogos de control previo del Ecuador (entidades y documentos).

Son datos de REFERENCIA públicos y estables (organismos y tipos de documento). Las
restricciones por subpartida (qué documento aplica a qué mercancía) se cargan aparte.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import ControlAuthority, ControlDocument

# (code, name, kind)
AUTHORITIES: list[tuple[str, str, str]] = [
    ("INEN", "Servicio Ecuatoriano de Normalización", "Normalización"),
    ("ARCSA", "Agencia Nacional de Regulación, Control y Vigilancia Sanitaria", "Sanitario"),
    ("AGROCALIDAD", "Agencia de Regulación y Control Fito y Zoosanitario", "Fito/Zoosanitario"),
    ("MSP", "Ministerio de Salud Pública", "Salud"),
    ("MPCEIP", "Ministerio de Producción, Comercio Exterior, Inversiones y Pesca", "Producción"),
    ("MAATE", "Ministerio del Ambiente, Agua y Transición Ecológica", "Ambiente/CITES"),
    ("ARCOTEL", "Agencia de Regulación y Control de las Telecomunicaciones", "Telecom"),
    ("SENADI", "Servicio Nacional de Derechos Intelectuales", "Propiedad intelectual"),
    ("MTOP", "Ministerio de Transporte y Obras Públicas", "Transporte"),
    ("ANT", "Agencia Nacional de Tránsito", "Tránsito"),
    ("CCFFAA", "Comando Conjunto de las Fuerzas Armadas", "Armas/explosivos"),
    ("MINEDUC", "Ministerio de Educación", "Educación"),
]

# (code, name, authority_code, description)
DOCUMENTS: list[tuple[str, str, str, str]] = [
    ("INEN-1", "Certificado de Reconocimiento (INEN-1)", "INEN", "Reglamentos técnicos ecuatorianos"),
    ("RS-ARCSA", "Registro Sanitario / Notificación Sanitaria Obligatoria", "ARCSA", "Alimentos, medicamentos, cosméticos, etc."),
    ("FITO", "Certificado Fitosanitario", "AGROCALIDAD", "Vegetales y productos de origen vegetal"),
    ("ZOO", "Certificado Zoosanitario", "AGROCALIDAD", "Animales y productos de origen animal"),
    ("AFE-MAATE", "Autorización/permiso ambiental (incl. CITES)", "MAATE", "Especies, sustancias controladas"),
    ("HOMOLOG-ARCOTEL", "Homologación / certificación", "ARCOTEL", "Equipos de telecomunicaciones"),
    ("ARMAS-CCFFAA", "Autorización de importación de armas/explosivos", "CCFFAA", "Armas, municiones, explosivos"),
]


async def seed_control_catalog(session: AsyncSession) -> dict:
    existing_auth = {a.code for a in await session.scalars(select(ControlAuthority.code))}
    auth_by_code: dict[str, ControlAuthority] = {}
    created_a = 0
    for code, name, kind in AUTHORITIES:
        if code in existing_auth:
            auth_by_code[code] = await session.scalar(
                select(ControlAuthority).where(ControlAuthority.code == code)
            )
            continue
        a = ControlAuthority(code=code, name=name, kind=kind)
        session.add(a)
        await session.flush()
        auth_by_code[code] = a
        created_a += 1

    existing_doc = {d.code for d in await session.scalars(select(ControlDocument.code))}
    created_d = 0
    for code, name, auth_code, desc in DOCUMENTS:
        if code in existing_doc:
            continue
        auth = auth_by_code.get(auth_code)
        session.add(ControlDocument(
            code=code, name=name, authority_id=(auth.id if auth else None), description=desc
        ))
        created_d += 1
    await session.flush()
    return {"authorities_created": created_a, "documents_created": created_d}
