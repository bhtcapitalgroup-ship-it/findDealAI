"""Document management API endpoints."""

import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.document import (
    DocumentAnalysisResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    doc_type: str | None = Query(None),
    property_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List documents, filterable by type and property."""
    stmt = select(Document).where(
        Document.landlord_id == current_user.id,
        Document.is_deleted == False,
    )

    if doc_type is not None:
        stmt = stmt.where(Document.doc_type == doc_type)
    if property_id is not None:
        stmt = stmt.where(Document.property_id == property_id)

    stmt = (
        stmt.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    property_id: UUID | None = Form(None),
    unit_id: UUID | None = Form(None),
    tenant_id: UUID | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a document. Receives the file and stores metadata.

    In production, the file bytes are uploaded to S3. Here we generate a
    placeholder S3 key.
    """
    # Read file to get size (in production, stream to S3)
    content = await file.read()
    file_size = len(content)

    # S3 upload placeholder — generates a fake S3 key
    s3_key = (
        f"documents/{current_user.id}/{uuid_mod.uuid4().hex[:12]}/"
        f"{file.filename}"
    )

    doc = Document(
        landlord_id=current_user.id,
        property_id=property_id,
        unit_id=unit_id,
        tenant_id=tenant_id,
        doc_type=doc_type,
        filename=file.filename or "untitled",
        s3_key=s3_key,
        file_size=file_size,
        mime_type=file.content_type,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return DocumentUploadResponse.model_validate(doc)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get document metadata."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.is_deleted == False,
        )
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if doc.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document",
        )
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.is_deleted == False,
        )
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if doc.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document",
        )

    doc.is_deleted = True
    await db.flush()


@router.post("/{document_id}/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentAnalysisResponse:
    """Trigger AI lease analysis on a document.

    In production, this downloads the PDF from S3, runs OCR if needed,
    and sends the text to an LLM for structured analysis.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.is_deleted == False,
        )
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if doc.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to analyze this document",
        )

    # AI integration placeholder — will call lease_analyzer.analyze()
    # In production: download from S3 -> OCR -> LLM extraction
    analysis = {
        "document_type": "residential_lease",
        "parties": {
            "landlord": "Property Owner LLC",
            "tenant": "Jane Doe",
        },
        "key_terms": {
            "rent_amount": 1500.00,
            "lease_start": "2025-01-01",
            "lease_end": "2025-12-31",
            "deposit": 1500.00,
            "late_fee": 50.00,
            "grace_period_days": 5,
        },
        "clauses_of_note": [
            "No subletting without written consent",
            "Landlord responsible for major repairs",
            "60-day notice required for non-renewal",
        ],
        "risk_flags": [
            "No specific mold disclosure clause",
        ],
        "confidence": 0.92,
    }

    doc.ai_analysis = analysis
    await db.flush()
    await db.refresh(doc)

    return DocumentAnalysisResponse(
        document_id=doc.id,
        analysis=analysis,
    )
