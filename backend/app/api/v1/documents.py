"""Endpoints de Documentos: subida con versionado e integridad SHA-256."""

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.document import Document, DocumentExtraction, DocumentVersion
from app.models.shipment import CaseEvent
from app.schemas.document import (
    CaseExtractionDoc,
    DocumentExtractionRead,
    DocumentExtractionUpdate,
    DocumentRead,
    ExtractedFieldPreview,
    ExtractionPreview,
    PresignedUrl,
)
from app.services.doc_linking import autolink_document
from app.services.extraction import Extractor, extract_transport, get_extractor
from app.services.storage import StorageService, get_storage, sha256_hex

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Tipos de documento con datos estructurados que vale la pena extraer al subir.
EXTRACTABLE_DOC_TYPES = {
    "COMMERCIAL_INVOICE", "INVOICE", "PROFORMA", "PROFORMA_INVOICE",
    "PACKING_LIST", "BILL_OF_LADING", "AIR_WAYBILL", "CERTIFICATE_OF_ORIGIN",
}


def _should_auto_extract(doc_type: str | None) -> bool:
    return (doc_type or "").upper() in EXTRACTABLE_DOC_TYPES


async def _persist_extraction(
    session: AsyncSession,
    storage: StorageService,
    extractor: Extractor,
    dv: DocumentVersion,
) -> list[DocumentExtraction]:
    """Ejecuta el extractor (OCR incluido) fuera del event loop y guarda los campos."""
    data = await run_in_threadpool(storage.get_bytes, dv.object_key)
    result = await run_in_threadpool(extractor.extract, data, dv.content_type, dv.filename)
    rows: list[DocumentExtraction] = []
    for f in result.fields:
        row = DocumentExtraction(
            document_version_id=dv.id,
            field_name=f.field_name,
            extracted_value=f.value,
            confidence_score=f.confidence,
            source_page=f.source_page,
            model_version=result.model_version,
        )
        session.add(row)
        rows.append(row)
    await session.flush()
    return rows


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
    customs_case_id: uuid.UUID | None = Form(None),
    doc_type: str = Form("UNCLASSIFIED"),
    source: str = Form("PORTAL"),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> Document:
    document = Document(
        customer_id=customer_id,
        customs_case_id=customs_case_id,
        doc_type=doc_type,
        source=source,
    )
    session.add(document)
    await session.flush()  # asigna document.id
    dv = await _store_version(session, storage, document, file, version=1)
    await session.flush()
    # AUTOMATION: si el doc pertenece a un expediente y su tipo calza, completa el checklist.
    await autolink_document(session, document)
    await session.flush()

    # AUTOMATION: extracción automática (OCR/heurística) para documentos con datos.
    # Best-effort: si falla, NO se rompe la subida.
    if _should_auto_extract(document.doc_type):
        try:
            rows = await _persist_extraction(session, storage, get_extractor(), dv)
            if rows and document.customs_case_id:
                session.add(
                    CaseEvent(
                        customs_case_id=document.customs_case_id,
                        event_type="DOCUMENT_EXTRACTED",
                        event_source="SYSTEM",
                        normalized_payload={
                            "doc_type": document.doc_type,
                            "recognized": sum(1 for r in rows if r.extracted_value),
                            "model": rows[0].model_version,
                        },
                    )
                )
                await session.flush()
        except Exception:  # noqa: BLE001
            logger.exception("Auto-extracción falló para %s (no bloquea la subida)", document.id)

    await session.refresh(document)
    return document


@router.post("/extract-preview", response_model=ExtractionPreview)
async def extract_preview(
    file: UploadFile = File(...),
    extractor: Extractor = Depends(get_extractor),
) -> ExtractionPreview:
    """Extrae datos de un archivo SIN persistirlo, para prellenar formularios.

    Úsalo al crear una cotización: sube la proforma y prellena incoterm, moneda y
    montos para revisión humana. No guarda el archivo ni la extracción.
    """
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Archivo vacío")
    result = await run_in_threadpool(extractor.extract, data, file.content_type, file.filename)
    return ExtractionPreview(
        model_version=result.model_version,
        fields=[
            ExtractedFieldPreview(field_name=f.field_name, value=f.value, confidence=f.confidence)
            for f in result.fields
        ],
    )


@router.post("/extract-transport-preview", response_model=ExtractionPreview)
async def extract_transport_preview(
    file: UploadFile = File(...),
) -> ExtractionPreview:
    """Extrae datos de transporte de un BL/AWB SIN persistirlo, para prellenar el embarque."""
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Archivo vacío")
    result = await run_in_threadpool(extract_transport, data, file.content_type, file.filename)
    return ExtractionPreview(
        model_version=result.model_version,
        fields=[
            ExtractedFieldPreview(field_name=f.field_name, value=f.value, confidence=f.confidence)
            for f in result.fields
        ],
    )


@router.post("/{document_id}/attach", response_model=dict)
async def attach_to_case(
    document_id: uuid.UUID,
    customs_case_id: uuid.UUID,
    doc_type: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Asocia un documento existente a un expediente y auto-vincula el checklist."""
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    document.customs_case_id = customs_case_id
    if doc_type:
        document.doc_type = doc_type
    await session.flush()
    item = await autolink_document(session, document)
    await session.flush()
    return {
        "matched": item is not None,
        "checklist_item_id": str(item.id) if item else None,
        "doc_type": document.doc_type,
    }


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
    customs_case_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Document]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if customer_id is not None:
        stmt = stmt.where(Document.customer_id == customer_id)
    if customs_case_id is not None:
        stmt = stmt.where(Document.customs_case_id == customs_case_id)
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


async def _get_version_or_404(
    session: AsyncSession, document_id: uuid.UUID, version: int
) -> DocumentVersion:
    dv = await session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document_id, DocumentVersion.version == version
        )
    )
    if dv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada")
    return dv


@router.post(
    "/{document_id}/versions/{version}/extract",
    response_model=list[DocumentExtractionRead],
    status_code=status.HTTP_201_CREATED,
)
async def extract_version(
    document_id: uuid.UUID,
    version: int,
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> list[DocumentExtraction]:
    dv = await _get_version_or_404(session, document_id, version)
    return await _persist_extraction(session, storage, extractor, dv)


@router.patch(
    "/{document_id}/versions/{version}/extractions/{extraction_id}",
    response_model=DocumentExtractionRead,
)
async def verify_extraction(
    document_id: uuid.UUID,
    version: int,
    extraction_id: uuid.UUID,
    payload: DocumentExtractionUpdate,
    session: AsyncSession = Depends(get_session),
) -> DocumentExtraction:
    """Revisión humana: fija/corrige el valor verificado de un campo extraído."""
    dv = await _get_version_or_404(session, document_id, version)
    row = await session.get(DocumentExtraction, extraction_id)
    if row is None or row.document_version_id != dv.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Extracción no encontrada")
    row.verified_value = payload.verified_value
    await session.flush()
    return row


@router.get("/case/{case_id}/extractions", response_model=list[CaseExtractionDoc])
async def case_extractions(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[CaseExtractionDoc]:
    """Datos extraídos de todos los documentos de un expediente (para revisión)."""
    docs = list(
        await session.scalars(
            select(Document)
            .where(Document.customs_case_id == case_id)
            .order_by(Document.created_at.desc())
        )
    )
    out: list[CaseExtractionDoc] = []
    for doc in docs:
        dv = doc.latest_version
        if dv is None:
            continue
        rows = list(
            await session.scalars(
                select(DocumentExtraction)
                .where(DocumentExtraction.document_version_id == dv.id)
                .order_by(DocumentExtraction.confidence_score.desc())
            )
        )
        if not rows:
            continue
        out.append(
            CaseExtractionDoc(
                document_id=doc.id,
                version=dv.version,
                doc_type=doc.doc_type,
                filename=dv.filename,
                model_version=rows[0].model_version,
                fields=[DocumentExtractionRead.model_validate(r) for r in rows],
            )
        )
    return out


@router.get(
    "/{document_id}/versions/{version}/extractions",
    response_model=list[DocumentExtractionRead],
)
async def list_extractions(
    document_id: uuid.UUID,
    version: int,
    session: AsyncSession = Depends(get_session),
) -> list[DocumentExtraction]:
    dv = await _get_version_or_404(session, document_id, version)
    result = await session.scalars(
        select(DocumentExtraction).where(DocumentExtraction.document_version_id == dv.id)
    )
    return list(result)


@router.get("/{document_id}/versions/{version}/download", response_model=PresignedUrl)
async def download_version(
    document_id: uuid.UUID,
    version: int,
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> PresignedUrl:
    dv = await _get_version_or_404(session, document_id, version)
    url = await run_in_threadpool(storage.presigned_get_url, dv.object_key, 3600)
    return PresignedUrl(url=url, expires_seconds=3600)
