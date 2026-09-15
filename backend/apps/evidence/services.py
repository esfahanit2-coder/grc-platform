import hashlib
import io
import mimetypes
import uuid
from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.actions.models import Action
from apps.assessments.models import Assessment, AssessmentItem
from apps.common.storage import S3ObjectStorage
from apps.controls.models import ControlImplementation
from apps.frameworks.models import Requirement
from apps.risks.models import Risk

SUPPORTED_LINK_TYPES = {"assessment", "assessment_item", "control_implementation", "risk", "finding", "action", "requirement", "audit_workpaper", "control_test_run", "document"}


def link_scope(tenant, object_type, object_id):
    if object_type not in SUPPORTED_LINK_TYPES:
        raise ValidationError({"object_type": "Unsupported evidence link target."})
    if object_type == "assessment":
        obj = Assessment.objects.filter(id=object_id, tenant=tenant, deleted_at__isnull=True).first()
        return obj, obj.organization_unit if obj else None
    if object_type == "assessment_item":
        obj = AssessmentItem.objects.select_related("assessment__organization_unit").filter(id=object_id, assessment__tenant=tenant, deleted_at__isnull=True).first()
        return obj, obj.assessment.organization_unit if obj else None
    if object_type == "control_implementation":
        obj = ControlImplementation.objects.filter(id=object_id, tenant=tenant, deleted_at__isnull=True).select_related("organization_unit").first()
        return obj, obj.organization_unit if obj else None
    if object_type == "risk":
        obj = Risk.objects.filter(id=object_id, tenant=tenant, deleted_at__isnull=True).select_related("organization_unit").first()
        return obj, obj.organization_unit if obj else None
    if object_type == "action":
        obj = Action.objects.filter(id=object_id, tenant=tenant, deleted_at__isnull=True).select_related("organization_unit").first()
        return obj, obj.organization_unit if obj else None

    if object_type == "audit_workpaper":
        from apps.internal_audits.models import Workpaper
        obj=Workpaper.objects.select_related("engagement__organization_unit").filter(id=object_id,engagement__tenant=tenant,deleted_at__isnull=True).first();return obj,obj.engagement.organization_unit if obj else None
    if object_type == "control_test_run":
        from apps.controls.models import ControlTestRun
        obj=ControlTestRun.objects.select_related("control_test__control_implementation__organization_unit").filter(id=object_id,control_test__control_implementation__tenant=tenant,deleted_at__isnull=True).first();return obj,obj.control_test.control_implementation.organization_unit if obj else None
    if object_type == "document":
        from apps.documents.models import Document
        obj=Document.objects.select_related("organization_unit").filter(id=object_id,tenant=tenant,deleted_at__isnull=True).first();return obj,obj.organization_unit if obj else None
    if object_type == "finding":
        from apps.findings.models import Finding
        obj = Finding.objects.filter(id=object_id, tenant=tenant, deleted_at__isnull=True).select_related("organization_unit").first()
        return obj, obj.organization_unit if obj else None
    obj = Requirement.objects.filter(id=object_id, deleted_at__isnull=True).select_related("framework_version__framework").first()
    if obj and obj.framework_version.framework.tenant_id not in {None, tenant.id}:
        obj = None
    return obj, None


def store_uploaded_evidence(evidence, uploaded):
    max_size = int(getattr(settings, "EVIDENCE_MAX_FILE_SIZE", 25 * 1024 * 1024))
    if uploaded.size > max_size:
        raise ValidationError({"file": f"Evidence file exceeds maximum size of {max_size} bytes."})
    raw = uploaded.read()
    digest = hashlib.sha256(raw).hexdigest()
    safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
    key = f"tenant/{evidence.tenant_id}/evidence/{evidence.id}/{uuid.uuid4().hex}-{safe_name}"
    content_type = getattr(uploaded, "content_type", "") or mimetypes.guess_type(uploaded.name)[0] or "application/octet-stream"
    S3ObjectStorage().put(key, io.BytesIO(raw), content_type=content_type)
    evidence.storage_key = key
    evidence.original_filename = uploaded.name[:255]
    evidence.mime_type = content_type[:160]
    evidence.size = len(raw)
    evidence.sha256 = digest
    metadata = dict(evidence.metadata or {})
    metadata.setdefault("malware_scan_status", "not_scanned")
    evidence.metadata = metadata
    evidence.save(update_fields=["storage_key", "original_filename", "mime_type", "size", "sha256", "metadata", "updated_at"])
    return evidence
