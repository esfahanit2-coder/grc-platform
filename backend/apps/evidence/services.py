import hashlib
import io
import mimetypes
import uuid

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.common.domain_registry import (
    domain_object_scope,
    registered_type_codes,
    resolve_domain_object,
)
from apps.common.storage import S3ObjectStorage

from .malware import SERVER_MANAGED_MALWARE_METADATA_KEYS, scanner_backend

SUPPORTED_LINK_TYPES = registered_type_codes(capability="evidence_link")

# Active/executable formats are not useful as inline GRC evidence and create a
# disproportionate execution/XSS risk if later served by an object store.
BLOCKED_EVIDENCE_EXTENSIONS = {
    ".bat", ".cmd", ".com", ".dll", ".exe", ".hta", ".htm", ".html",
    ".jar", ".js", ".jse", ".msi", ".msp", ".ps1", ".scr", ".svg",
    ".vbe", ".vbs", ".wsf", ".wsh",
}
BLOCKED_EVIDENCE_MIME_TYPES = {
    "application/javascript",
    "application/x-javascript",
    "application/x-msdownload",
    "application/x-msdos-program",
    "image/svg+xml",
    "text/html",
    "text/javascript",
}


def link_scope(tenant, object_type, object_id):
    obj = resolve_domain_object(
        tenant=tenant,
        type_code=object_type,
        object_id=object_id,
        capability="evidence_link",
    )
    if obj is None:
        return None, None
    return obj, domain_object_scope(obj, object_type)


def _safe_upload_name(uploaded):
    raw_name = str(getattr(uploaded, "name", "") or "upload.bin")
    return raw_name.replace("\\", "/").rsplit("/", 1)[-1] or "upload.bin"


def validate_evidence_upload(uploaded):
    max_size = int(getattr(settings, "EVIDENCE_MAX_FILE_SIZE", 25 * 1024 * 1024))
    if uploaded.size > max_size:
        raise ValidationError({"file": f"Evidence file exceeds maximum size of {max_size} bytes."})

    safe_name = _safe_upload_name(uploaded)
    lowered = safe_name.lower()
    extension = "." + lowered.rsplit(".", 1)[-1] if "." in lowered else ""
    content_type = (
        getattr(uploaded, "content_type", "")
        or mimetypes.guess_type(safe_name)[0]
        or "application/octet-stream"
    ).split(";", 1)[0].strip().lower()

    if extension in BLOCKED_EVIDENCE_EXTENSIONS or content_type in BLOCKED_EVIDENCE_MIME_TYPES:
        raise ValidationError({"file": "Active or executable file types are not accepted as evidence."})
    return safe_name, content_type


def store_uploaded_evidence(evidence, uploaded):
    safe_name, content_type = validate_evidence_upload(uploaded)
    raw = uploaded.read()
    digest = hashlib.sha256(raw).hexdigest()
    key = f"tenant/{evidence.tenant_id}/evidence/{evidence.id}/{uuid.uuid4().hex}-{safe_name}"
    S3ObjectStorage().put(key, io.BytesIO(raw), content_type=content_type)
    evidence.storage_key = key
    evidence.original_filename = safe_name[:255]
    evidence.mime_type = content_type[:160]
    evidence.size = len(raw)
    evidence.sha256 = digest
    metadata = dict(evidence.metadata or {})
    # A new blob invalidates every previous scanner claim. Server-managed scan
    # keys are cleared even for internal callers before the new pending state is
    # established.
    for key_name in SERVER_MANAGED_MALWARE_METADATA_KEYS:
        metadata.pop(key_name, None)
    metadata["malware_scan_status"] = "pending"
    metadata["malware_scan_required"] = True
    metadata["malware_scan_scanner"] = scanner_backend()
    metadata["malware_scan_attempts"] = 0
    evidence.metadata = metadata
    evidence.save(update_fields=["storage_key", "original_filename", "mime_type", "size", "sha256", "metadata", "updated_at"])
    return evidence
