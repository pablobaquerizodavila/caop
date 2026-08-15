"""Endpoints de Clientes, Contactos y Consentimiento (LOPDP)."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import ConsentRecord, Contact, Customer
from app.models.document import Document
from app.models.notification import Notification
from app.models.quote import Quote
from app.models.shipment import CustomsCase, Shipment
from app.schemas.customer import (
    ConsentCreate,
    ConsentRead,
    ContactCreate,
    ContactRead,
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
)

router = APIRouter(prefix="/customers", tags=["customers"])


async def _get_customer_or_404(session: AsyncSession, customer_id: uuid.UUID) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return customer


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate, session: AsyncSession = Depends(get_session)
) -> Customer:
    existing = await session.scalar(select(Customer).where(Customer.ruc == payload.ruc))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese RUC")

    customer = Customer(
        ruc=payload.ruc,
        legal_name=payload.legal_name,
        trade_name=payload.trade_name,
        entity_type=payload.entity_type,
        address=payload.address,
        legal_rep_name=payload.legal_rep_name,
        legal_rep_id=payload.legal_rep_id,
        email=payload.email,
        billing_data=payload.billing_data,
        notification_prefs=payload.notification_prefs,
        status=payload.status,
    )
    for c in payload.contacts:
        customer.contacts.append(Contact(**c.model_dump()))
    session.add(customer)
    await session.flush()
    await session.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Customer]:
    result = await session.scalars(
        select(Customer).order_by(Customer.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Customer:
    return await _get_customer_or_404(session, customer_id)


@router.get("/{customer_id}/history")
async def customer_history(
    customer_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    """Panel del cliente: sus expedientes de importación y cotizaciones."""
    customer = await _get_customer_or_404(session, customer_id)

    rows = await session.execute(
        select(CustomsCase, Shipment, Quote.quote_number)
        .join(Shipment, CustomsCase.shipment_id == Shipment.id)
        .join(Quote, Shipment.source_quote_id == Quote.id, isouter=True)
        .where(Shipment.customer_id == customer_id)
        .order_by(CustomsCase.created_at.desc())
    )
    cases = [
        {
            "id": str(case.id),
            "case_number": case.case_number,
            "current_state": case.current_state,
            "customs_readiness_score": float(case.customs_readiness_score or 0),
            "risk_level": case.risk_level,
            "transport_mode": shipment.transport_mode,
            "origin_country": shipment.origin_country,
            "source_quote_number": qnum,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        }
        for case, shipment, qnum in rows.all()
    ]

    # Mapa cotización -> nº de expediente (para la correlación inversa).
    qrows = await session.execute(
        select(Shipment.source_quote_id, CustomsCase.case_number)
        .join(CustomsCase, CustomsCase.shipment_id == Shipment.id)
        .where(Shipment.customer_id == customer_id)
    )
    quote_to_case = {qid: cnum for qid, cnum in qrows.all()}

    quotes = list(
        await session.scalars(
            select(Quote).where(Quote.customer_id == customer_id).order_by(Quote.created_at.desc())
        )
    )
    quote_list = [
        {
            "id": str(q.id),
            "quote_number": q.quote_number,
            "version": q.version,
            "status": q.status,
            "currency": q.currency,
            "landed_cost_total": float(q.landed_cost_total or 0),
            "case_number": quote_to_case.get(q.id),
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in quotes
    ]

    ready = sum(1 for c in cases if c["current_state"] == "READY_FOR_CUSTOMS")
    return {
        "customer": {
            "id": str(customer.id),
            "ruc": customer.ruc,
            "legal_name": customer.legal_name,
            "trade_name": customer.trade_name,
            "email": customer.email,
            "status": customer.status,
        },
        "stats": {
            "total_cases": len(cases),
            "ready_for_customs": ready,
            "total_quotes": len(quote_list),
        },
        "cases": cases,
        "quotes": quote_list,
    }


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    session: AsyncSession = Depends(get_session),
) -> Customer:
    customer = await _get_customer_or_404(session, customer_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await session.flush()
    await session.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    cascade: bool = Query(
        False,
        description="Si es true, borra también expedientes, cotizaciones, documentos y "
        "notificaciones del cliente. Si es false y hay historial, responde 409.",
    ),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Elimina un cliente. Por defecto protege el historial: si el cliente tiene
    expedientes, cotizaciones o documentos, responde 409 con el detalle; el borrado
    en cascada solo ocurre con `?cascade=true` (confirmación explícita)."""
    customer = await _get_customer_or_404(session, customer_id)

    n_ship = await session.scalar(
        select(func.count()).select_from(Shipment).where(Shipment.customer_id == customer_id)
    )
    n_quotes = await session.scalar(
        select(func.count()).select_from(Quote).where(Quote.customer_id == customer_id)
    )
    n_docs = await session.scalar(
        select(func.count()).select_from(Document).where(Document.customer_id == customer_id)
    )

    if (n_ship or n_quotes or n_docs) and not cascade:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"El cliente tiene {n_ship} expediente(s), {n_quotes} cotización(es) y "
                f"{n_docs} documento(s). Confirma para borrarlos en cascada."
            ),
        )

    if cascade:
        # Orden seguro respecto a las FKs sin ON DELETE CASCADE.
        case_ids = list(
            await session.scalars(
                select(CustomsCase.id)
                .join(Shipment, CustomsCase.shipment_id == Shipment.id)
                .where(Shipment.customer_id == customer_id)
            )
        )
        # 1) notificaciones (del cliente o de sus expedientes) — bloquean cases y cliente.
        notif_cond = [Notification.customer_id == customer_id]
        if case_ids:
            notif_cond.append(Notification.customs_case_id.in_(case_ids))
        await session.execute(delete(Notification).where(or_(*notif_cond)))
        # 2) expedientes vía shipment (cascada DB -> customs_case y sus hijos).
        await session.execute(delete(Shipment).where(Shipment.customer_id == customer_id))
        # 3) cotizaciones (cascada DB -> ítems, costos, historial, certificados).
        await session.execute(delete(Quote).where(Quote.customer_id == customer_id))
        # 4) documentos (cascada DB -> versiones y extracciones). Los checklist_item
        #    que los referencian ya se fueron con los expedientes.
        await session.execute(delete(Document).where(Document.customer_id == customer_id))

    # 5) el cliente (cascada DB -> contactos y consentimientos).
    await session.delete(customer)
    await session.flush()


@router.post(
    "/{customer_id}/contacts", response_model=ContactRead, status_code=status.HTTP_201_CREATED
)
async def add_contact(
    customer_id: uuid.UUID,
    payload: ContactCreate,
    session: AsyncSession = Depends(get_session),
) -> Contact:
    await _get_customer_or_404(session, customer_id)
    contact = Contact(customer_id=customer_id, **payload.model_dump())
    session.add(contact)
    await session.flush()
    await session.refresh(contact)
    return contact


@router.delete("/{customer_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    customer_id: uuid.UUID, contact_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    contact = await session.get(Contact, contact_id)
    if contact is None or contact.customer_id != customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contacto no encontrado")
    await session.delete(contact)
    await session.flush()


@router.post(
    "/{customer_id}/consents", response_model=ConsentRead, status_code=status.HTTP_201_CREATED
)
async def add_consent(
    customer_id: uuid.UUID,
    payload: ConsentCreate,
    session: AsyncSession = Depends(get_session),
) -> ConsentRecord:
    await _get_customer_or_404(session, customer_id)
    consent = ConsentRecord(customer_id=customer_id, **payload.model_dump())
    session.add(consent)
    await session.flush()
    await session.refresh(consent)
    return consent


@router.get("/{customer_id}/consents", response_model=list[ConsentRead])
async def list_consents(
    customer_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[ConsentRecord]:
    await _get_customer_or_404(session, customer_id)
    result = await session.scalars(
        select(ConsentRecord).where(ConsentRecord.customer_id == customer_id)
    )
    return list(result)


@router.post("/{customer_id}/consents/{consent_id}/revoke", response_model=ConsentRead)
async def revoke_consent(
    customer_id: uuid.UUID, consent_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ConsentRecord:
    """Revoca un consentimiento (LOPDP): registra la fecha de revocación."""
    consent = await session.get(ConsentRecord, consent_id)
    if consent is None or consent.customer_id != customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consentimiento no encontrado")
    consent.revoked_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(consent)
    return consent
