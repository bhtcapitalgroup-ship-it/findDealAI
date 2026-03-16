"""Document Service — Upload, download, and AI analysis of documents."""

import logging
import os
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Manages document uploads to S3, pre-signed download URLs,
    and triggering AI lease analysis.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        landlord_id: uuid.UUID,
        property_id: uuid.UUID | None = None,
        doc_type: str = "lease",
        mime_type: str = "application/pdf",
        unit_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> Document:
        """
        Upload a document to S3 and create a database record.

        In production, uploads to S3 via boto3:
            s3_client = boto3.client('s3')
            s3_client.put_object(
                Bucket=settings.S3_BUCKET,
                Key=s3_key,
                Body=file_content,
                ContentType=mime_type,
            )
        """
        # Generate a unique S3 key
        ext = os.path.splitext(filename)[1] or ".pdf"
        s3_key = (
            f"documents/{landlord_id}/{doc_type}/"
            f"{uuid.uuid4().hex}{ext}"
        )

        # Placeholder: upload to S3
        # In production:
        # import boto3
        # s3_client = boto3.client('s3')
        # s3_client.put_object(
        #     Bucket=settings.S3_BUCKET,
        #     Key=s3_key,
        #     Body=file_content,
        #     ContentType=mime_type,
        #     ServerSideEncryption='AES256',
        # )
        logger.info("S3 upload placeholder: %s (%d bytes)", s3_key, len(file_content))

        # Create database record
        document = Document(
            landlord_id=landlord_id,
            property_id=property_id,
            unit_id=unit_id,
            tenant_id=tenant_id,
            doc_type=doc_type,
            filename=filename,
            s3_key=s3_key,
            file_size=len(file_content),
            mime_type=mime_type,
        )
        self.db.add(document)
        await self.db.flush()

        logger.info(
            "Document %s uploaded: %s (type=%s, size=%d)",
            document.id,
            filename,
            doc_type,
            len(file_content),
        )

        return document

    # ------------------------------------------------------------------
    # Download URL
    # ------------------------------------------------------------------

    async def get_download_url(
        self,
        document_id: uuid.UUID,
        expiry_seconds: int = 3600,
    ) -> str:
        """
        Generate a pre-signed S3 download URL for a document.

        In production:
            s3_client = boto3.client('s3')
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.S3_BUCKET, 'Key': document.s3_key},
                ExpiresIn=expiry_seconds,
            )
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.is_deleted.is_(False),
            )
        )
        document = result.scalar_one()

        # Placeholder: generate pre-signed URL
        # In production:
        # import boto3
        # s3_client = boto3.client('s3')
        # url = s3_client.generate_presigned_url(
        #     'get_object',
        #     Params={
        #         'Bucket': settings.S3_BUCKET,
        #         'Key': document.s3_key,
        #     },
        #     ExpiresIn=expiry_seconds,
        # )
        # return url

        placeholder_url = (
            f"https://s3.amazonaws.com/realdeal-documents/"
            f"{document.s3_key}?X-Amz-Expires={expiry_seconds}"
            f"&X-Amz-Signature=placeholder"
        )

        logger.info(
            "Pre-signed URL generated for document %s (expires in %ds)",
            document_id,
            expiry_seconds,
        )

        return placeholder_url

    # ------------------------------------------------------------------
    # AI Analysis
    # ------------------------------------------------------------------

    async def trigger_analysis(
        self,
        document_id: uuid.UUID,
    ) -> dict:
        """
        Start lease analysis on a document.

        Extracts text from the document (via OCR if needed) and runs
        the AI lease analyzer to produce structured analysis.
        """
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one()

        # Get the document text (OCR text or raw text)
        lease_text = document.ocr_text
        if not lease_text:
            # In production, fetch from S3 and run OCR
            # For now, check if we can extract text from the stored content
            #
            # import boto3
            # s3_client = boto3.client('s3')
            # obj = s3_client.get_object(
            #     Bucket=settings.S3_BUCKET, Key=document.s3_key
            # )
            # raw_bytes = obj['Body'].read()
            #
            # # For PDF: use PyPDF2 or pdfplumber
            # import pdfplumber
            # with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            #     lease_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            #
            # # Update OCR text in database
            # document.ocr_text = lease_text

            logger.warning(
                "No OCR text available for document %s; analysis requires text content",
                document_id,
            )
            return {
                "status": "pending",
                "document_id": str(document_id),
                "reason": "no_text_content",
                "message": "Document text extraction is required before analysis can proceed.",
            }

        # Run the lease analyzer
        from app.ai.lease_analyzer import LeaseAnalyzerService

        analyzer = LeaseAnalyzerService(self.db)
        analysis = await analyzer.analyze_and_update(document_id, lease_text)

        logger.info(
            "Lease analysis triggered for document %s: risk_score=%d",
            document_id,
            analysis.risk_score,
        )

        return {
            "status": "completed",
            "document_id": str(document_id),
            "risk_score": analysis.risk_score,
            "risks_count": len(analysis.risks),
            "missing_clauses_count": len(analysis.missing_clauses),
            "summary": analysis.summary,
        }
