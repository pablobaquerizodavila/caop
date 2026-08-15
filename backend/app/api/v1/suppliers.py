"""Endpoints de Proveedores."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate, session: AsyncSession = Depends(get_session)
) -> Supplier:
    supplier = Supplier(**payload.model_dump())
    session.add(supplier)
    await session.flush()
    await session.refresh(supplier)
    return supplier


@router.get("", response_model=list[SupplierRead])
async def list_suppliers(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Supplier]:
    result = await session.scalars(
        select(Supplier).order_by(Supplier.name).limit(limit).offset(offset)
    )
    return list(result)


async def _supplier_or_404(session: AsyncSession, supplier_id: uuid.UUID) -> Supplier:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")
    return supplier


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Supplier:
    return await _supplier_or_404(session, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: uuid.UUID, payload: SupplierUpdate, session: AsyncSession = Depends(get_session)
) -> Supplier:
    supplier = await _supplier_or_404(session, supplier_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    await session.flush()
    await session.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    supplier = await _supplier_or_404(session, supplier_id)
    await session.delete(supplier)
    await session.flush()
