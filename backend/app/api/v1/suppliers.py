"""Endpoints de Proveedores."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierRead

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


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Supplier:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")
    return supplier
