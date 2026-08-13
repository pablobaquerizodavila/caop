"""Endpoints de Documentos: subida con versionado e integridad SHA-256."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.document import Document, DocumentVersion
from app.schemas.document import DocumentRead, PresignedUrl
from app.services.storage import StorageService, get_storage, sha256_hex

router = APIRouter(prefix="/documents", tags=["documents"])


def _object_key(document_id: uuid.UUID, version: int, filename: str) -> str:
    return f"documents/{document_id}/v{version}/{filename}"


async def _store_version(
    session: AsyncSession,
    storage: StorageService,
    document: Document,
    file: UploadFile,
    version: int,
) -> DocumentVersion:
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Archivo vacío")
    digest = sha256_hex(data)
    key = _object_key(document.id, version, file.filename or "archivo")

    await run_in_threadpool(storage.ensure_bucket)
    await run_in_threadpool(storage.put_object, key, data, file.content_type)

    dv = DocumentVersion(
        document_id=document.id,
        version=version,
        object_key=key,
        sha256=digest,
        size=len(data),
        content_type=file.content_type,
        filename=file.filename or "archivo",
    )
    session.add(dv)
    return dv


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    customer_id: uuid.UUID | None = Form(None),
    doc_type: str = Form("UNCLASSIFIED"),
    source: str = Form("PORTAL"),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> Document:
    document = Document(customer_id=customer_id, doc_type=doc_type, source=source)
    session.add(document)
    await session.flush()  # asigna document.id
    await _store_version(session, storage, document, file, version=1)
    await session.flush()
    await session.refresh(document)
    return document


@router.post("/{document_id}/versions", response_model=DocumentRead)
async def add_version(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")

    max_version = await session.scalar(
        select(func.max(DocumentVersion.version)).where(
            DocumentVersion.document_id == document_id
        )
    )
    await _store_version(session, storage, document, file, version=(max_version or 0) + 1)
    await session.flush()
    await session.refresh(document)
    return document


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    session: AsyncSession = Depends(get_session),
    customer_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Document]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if customer_id is not None:
        stmt = stmt.where(Document.customer_id == customer_id)
    result = await session.scalars(stmt.limit(limit).offset(offset))
    return list(result)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    return document


@router.get("/{document_id}/versions/{version}/download", response_model=PresignedUrl)
async def download_version(
    document_id: uuid.UUID,
    version: int,
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> PresignedUrl:
    dv = await session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document_id, DocumentVersion.version == version
        )
    )
    if dv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada")
    url = await run_in_threadpool(storage.presigned_get_url, dv.object_key, 3600)
    return PresignedUrl(url=url, expires_seconds=3600)
