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

SUPPORTED_LINK_TYPES = registered_type_codes(capability="evidence_link")def link_scope(tenant, object_type, object_id):
    obj = resolve_domain_object(
        tenant=tenant,
        type_code=object_type,
        object_id=object_id,
        capability="evidence_link",
    )
    if obj is None:
        return None, None
    return obj, domain_object_scope(obj, object_type)

