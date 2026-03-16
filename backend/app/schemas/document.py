"""Pydantic schemas for documents."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""

    id: UUID
    filename: str
    s3_key: str
    doc_type: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Full document metadata response."""

    id: UUID
    landlord_id: UUID
    property_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    doc_type: str
    filename: str
    s3_key: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    ai_analysis: Optional[dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentAnalysisResponse(BaseModel):
    """Response from AI document analysis."""

    document_id: UUID
    analysis: dict[str, Any]
