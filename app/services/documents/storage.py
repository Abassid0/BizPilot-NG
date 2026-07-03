"""
app/services/documents/storage.py
-----------------------------------
Handles uploading generated documents to Supabase Storage
and returning signed download URLs.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.core.config import settings
from app.core.constants import DocType, OutputFormat
from app.db.client import supabase


EXTENSION_MAP = {
    OutputFormat.PDF:  "pdf",
    OutputFormat.DOCX: "docx",
    OutputFormat.TEXT: "txt",
}

MIME_MAP = {
    OutputFormat.PDF:  "application/pdf",
    OutputFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    OutputFormat.TEXT: "text/plain",
}


async def upload_document(
    user_id: str,
    doc_type: DocType,
    file_bytes: bytes,
    output_format: OutputFormat,
) -> Optional[str]:
    """
    Upload a generated document to Supabase Storage.

    Returns the public/signed URL of the uploaded file,
    or None if the upload fails.

    Storage path: /{user_id}/{doc_type}/{timestamp}-{uuid}.{ext}
    """
    ext      = EXTENSION_MAP.get(output_format, "pdf")
    mime     = MIME_MAP.get(output_format, "application/pdf")
    ts       = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"{ts}-{uuid.uuid4().hex[:8]}.{ext}"
    path     = f"{user_id}/{doc_type}/{filename}"

    try:
        supabase.storage.from_(settings.supabase_bucket_name).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": mime},
        )

        # Generate a signed URL valid for 24 hours (86400 seconds)
        signed = supabase.storage.from_(settings.supabase_bucket_name).create_signed_url(
            path=path,
            expires_in=86400,
        )
        url = signed.get("signedURL") or signed.get("signedUrl")
        logger.info(f"Uploaded {doc_type} doc for user {user_id}: {path}")
        return url

    except Exception as e:
        logger.error(f"Supabase storage upload error: {e}")
        return None


async def get_signed_url(storage_path: str, expires_in: int = 86400) -> Optional[str]:
    """Regenerate a signed URL for an existing file path."""
    try:
        signed = supabase.storage.from_(settings.supabase_bucket_name).create_signed_url(
            path=storage_path,
            expires_in=expires_in,
        )
        return signed.get("signedURL") or signed.get("signedUrl")
    except Exception as e:
        logger.error(f"get_signed_url error: {e}")
        return None
