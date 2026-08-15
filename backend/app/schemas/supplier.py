"""Schemas de Proveedor."""

import uuid

from pydantic import BaseModel, ConfigDict


class SupplierBase(BaseModel):
    name: str
    country: str | None = None
    aliases: dict | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    aliases: dict | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
