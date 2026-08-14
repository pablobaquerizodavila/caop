"""Exportación de reportes a CSV (UTF-8 con BOM para Excel)."""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import Customer
from app.models.quote import Quote
from app.models.shipment import CustomsCase, Shipment
from app.services.payments_service import receivables

router = APIRouter(prefix="/exports", tags=["exports"])


def _csv_response(header: list[str], rows: list[list], filename: str) -> Response:
    buf = io.StringIO()
    buf.write("﻿")  # BOM: Excel reconoce UTF-8 y muestra acentos
    writer = csv.writer(buf, delimiter=";")  # ; = separador amigable con Excel en es-EC
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/receivables.csv")
async def receivables_csv(session: AsyncSession = Depends(get_session)) -> Response:
    rec = await receivables(session)
    rows = [
        [r["settlement_number"], r["customer"], r["currency"], r["total"], r["paid"],
         r["balance"], r["due_date"] or "", r["days_overdue"], r["bucket"]]
        for r in rec["items"]
    ]
    header = ["Liquidacion", "Cliente", "Moneda", "Total", "Pagado", "Saldo",
              "Vence", "Dias_vencido", "Aging"]
    return _csv_response(header, rows, "cuentas_por_cobrar.csv")


@router.get("/cases.csv")
async def cases_csv(session: AsyncSession = Depends(get_session)) -> Response:
    result = await session.execute(
        select(CustomsCase, Customer.legal_name, Shipment.transport_mode, Shipment.origin_country)
        .join(Shipment, CustomsCase.shipment_id == Shipment.id)
        .join(Customer, Shipment.customer_id == Customer.id, isouter=True)
        .order_by(CustomsCase.created_at.desc())
    )
    rows = []
    for case, customer, mode, origin in result.all():
        rows.append([
            case.case_number, customer or "", case.current_state,
            float(case.customs_readiness_score or 0), case.risk_level, mode or "", origin or "",
            case.blocker or "", case.created_at.strftime("%Y-%m-%d") if case.created_at else "",
        ])
    header = ["Expediente", "Cliente", "Estado", "Readiness", "Riesgo", "Modo",
              "Origen", "Bloqueo", "Creado"]
    return _csv_response(header, rows, "expedientes.csv")


@router.get("/quotes.csv")
async def quotes_csv(session: AsyncSession = Depends(get_session)) -> Response:
    result = await session.execute(
        select(Quote, Customer.legal_name)
        .join(Customer, Quote.customer_id == Customer.id, isouter=True)
        .order_by(Quote.created_at.desc())
    )
    rows = []
    for q, customer in result.all():
        rows.append([
            q.quote_number, q.version, customer or "", q.status, q.currency,
            float(q.customer_price_total or 0), float(q.landed_cost_total or 0),
            q.valid_until.strftime("%Y-%m-%d") if q.valid_until else "",
            q.created_at.strftime("%Y-%m-%d") if q.created_at else "",
        ])
    header = ["Cotizacion", "Version", "Cliente", "Estado", "Moneda",
              "Precio_cliente", "Landed_cost", "Valida_hasta", "Creado"]
    return _csv_response(header, rows, "cotizaciones.csv")
