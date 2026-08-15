"""Carga inicial del Arancel del Ecuador desde el PDF oficial (bootstrap de producción).

Uso (dentro del contenedor backend):
    python -m app.scripts.load_arancel <ruta_pdf> <version> <YYYY-MM-DD>

Ejemplo:
    python -m app.scripts.load_arancel /app/arancel.pdf COMEX-002-2023 2023-09-01

Es idempotente en lo general (FODINFA/IVA no se duplican) e inserta una nueva
versión arancelaria STAGED que luego publica (supersede la anterior si existía).
"""

import asyncio
import sys
from datetime import date

from app.db.session import get_sessionmaker
from app.services.tariff_ingest import import_arancel, publish_version
from app.services.tax_seed import seed_ecuador_defaults


async def _run(path: str, version: str, effective_from: str) -> None:
    maker = get_sessionmaker()
    async with maker() as session:
        seeded = await seed_ecuador_defaults(session)
        if seeded:
            print(f">> Reglas generales sembradas (UNVERIFIED, verificar): {seeded}")
        print(">> Parseando e ingiriendo el arancel (puede tardar ~30-40s)…")
        res = await import_arancel(
            session, version_number=version,
            effective_from=date.fromisoformat(effective_from), path=path,
        )
        await publish_version(session, res.version_id)
        await session.commit()
        print(f">> LISTO: versión {version} ACTIVA — {res.codes} códigos, {res.rules} reglas Ad-Valorem")
        if res.errors:
            print(f">> Avisos de validación ({len(res.errors)}): {res.errors[:5]}")


def main() -> None:
    if len(sys.argv) != 4:
        print("Uso: python -m app.scripts.load_arancel <ruta_pdf> <version> <YYYY-MM-DD>")
        raise SystemExit(2)
    asyncio.run(_run(sys.argv[1], sys.argv[2], sys.argv[3]))


if __name__ == "__main__":
    main()
