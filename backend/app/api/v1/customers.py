"""Endpoints de Clientes, Contactos y Consentimiento (LOPDP)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import ConsentRecord, Contact, Customer
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
        address=payload.address,
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
