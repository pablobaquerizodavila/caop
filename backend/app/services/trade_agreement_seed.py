"""Semilla de acuerdos comerciales vigentes de Ecuador y catálogo de países.

Los acuerdos se siembran como METADATA (miembros, vigencia). Las preferencias por
subpartida viven en los anexos de desgravación de cada acuerdo (deben cargarse y
verificarse). Se siembra UNA preferencia base: la zona de libre comercio de la CAN
(0% para mercancías originarias de Bolivia/Colombia/Perú), marcada para verificar
sus excepciones (p. ej. productos del SAFP).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Country, TariffPreference, TradeAgreement

# (iso2, iso3, nombre)
COUNTRIES: list[tuple[str, str, str]] = [
    ("EC", "ECU", "Ecuador"),
    ("BO", "BOL", "Bolivia"), ("CO", "COL", "Colombia"), ("PE", "PER", "Perú"),
    ("AR", "ARG", "Argentina"), ("BR", "BRA", "Brasil"), ("PY", "PRY", "Paraguay"),
    ("UY", "URY", "Uruguay"),
    ("CN", "CHN", "China"), ("US", "USA", "Estados Unidos"), ("GB", "GBR", "Reino Unido"),
    ("CL", "CHL", "Chile"), ("MX", "MEX", "México"), ("CR", "CRI", "Costa Rica"),
    ("GT", "GTM", "Guatemala"), ("SV", "SLV", "El Salvador"), ("NI", "NIC", "Nicaragua"),
    ("IS", "ISL", "Islandia"), ("LI", "LIE", "Liechtenstein"), ("NO", "NOR", "Noruega"),
    ("CH", "CHE", "Suiza"),
    # Unión Europea (27)
    ("DE", "DEU", "Alemania"), ("FR", "FRA", "Francia"), ("ES", "ESP", "España"),
    ("IT", "ITA", "Italia"), ("NL", "NLD", "Países Bajos"), ("BE", "BEL", "Bélgica"),
    ("PT", "PRT", "Portugal"), ("PL", "POL", "Polonia"), ("SE", "SWE", "Suecia"),
    ("AT", "AUT", "Austria"), ("IE", "IRL", "Irlanda"), ("DK", "DNK", "Dinamarca"),
    ("FI", "FIN", "Finlandia"), ("GR", "GRC", "Grecia"), ("CZ", "CZE", "Chequia"),
    ("RO", "ROU", "Rumania"), ("HU", "HUN", "Hungría"), ("BG", "BGR", "Bulgaria"),
    ("SK", "SVK", "Eslovaquia"), ("HR", "HRV", "Croacia"), ("SI", "SVN", "Eslovenia"),
    ("LT", "LTU", "Lituania"), ("LV", "LVA", "Letonia"), ("EE", "EST", "Estonia"),
    ("LU", "LUX", "Luxemburgo"), ("CY", "CYP", "Chipre"), ("MT", "MLT", "Malta"),
]

_EU = [
    "DE", "FR", "ES", "IT", "NL", "BE", "PT", "PL", "SE", "AT", "IE", "DK", "FI", "GR",
    "CZ", "RO", "HU", "BG", "SK", "HR", "SI", "LT", "LV", "EE", "LU", "CY", "MT",
]

# (code, name, kind, members, effective_from)
AGREEMENTS: list[tuple[str, str, str, list[str], date | None]] = [
    ("CAN", "Comunidad Andina", "CUSTOMS_UNION", ["BO", "CO", "PE"], date(1997, 1, 1)),
    ("MERCOSUR", "MERCOSUR (ACE-59)", "PARTIAL", ["AR", "BR", "PY", "UY"], date(2005, 4, 1)),
    ("EU", "Acuerdo Comercial Multipartes Ecuador–Unión Europea", "FTA", _EU, date(2017, 1, 1)),
    ("EFTA", "Ecuador–EFTA", "FTA", ["IS", "LI", "NO", "CH"], date(2020, 11, 1)),
    ("CHINA", "TLC Ecuador–China", "FTA", ["CN"], date(2024, 5, 1)),
    ("CHILE", "ACE-65 Ecuador–Chile", "FTA", ["CL"], date(2010, 1, 25)),
    ("MEXICO", "ACE-29 Ecuador–México (ALADI)", "PARTIAL", ["MX"], None),
    ("GUATEMALA", "Ecuador–Guatemala", "PARTIAL", ["GT"], None),
    ("ELSALVADOR", "Ecuador–El Salvador", "PARTIAL", ["SV"], None),
    ("COSTARICA", "Ecuador–Costa Rica", "FTA", ["CR"], None),
    ("NICARAGUA", "Ecuador–Nicaragua", "PARTIAL", ["NI"], None),
    ("UK", "Acuerdo Comercial Ecuador–Reino Unido", "FTA", ["GB"], date(2021, 1, 1)),
]


async def seed_countries(session: AsyncSession) -> int:
    existing = {c.iso2 for c in await session.scalars(select(Country.iso2))}
    created = 0
    for iso2, iso3, name in COUNTRIES:
        if iso2 in existing:
            continue
        session.add(Country(iso2=iso2, iso3=iso3, name=name))
        created += 1
    await session.flush()
    return created


async def seed_agreements(session: AsyncSession) -> list[str]:
    existing = {a.code for a in await session.scalars(select(TradeAgreement.code))}
    created: list[str] = []
    can_id = None
    for code, name, kind, members, eff in AGREEMENTS:
        if code in existing:
            if code == "CAN":
                can_id = (await session.scalar(
                    select(TradeAgreement).where(TradeAgreement.code == "CAN")
                )).id
            continue
        ag = TradeAgreement(code=code, name=name, kind=kind, members=members, effective_from=eff)
        session.add(ag)
        await session.flush()
        created.append(code)
        if code == "CAN":
            can_id = ag.id

    # Preferencia base CAN: zona de libre comercio (0% para originarios). UNVERIFIED:
    # verificar excepciones (SAFP/agropecuarios) contra la normativa andina.
    if can_id is not None:
        has_pref = await session.scalar(
            select(TariffPreference).where(TariffPreference.agreement_id == can_id)
        )
        if has_pref is None:
            session.add(TariffPreference(
                agreement_id=can_id, origin_country=None, hs_prefix=None,
                liberation_pct=100, requires_certificate=True,
                effective_from=date(1997, 1, 1), status="ACTIVE", verification_status="UNVERIFIED",
                legal_source="CAN — zona de libre comercio (verificar excepciones SAFP/agro)",
            ))
            await session.flush()
    return created
