"""Administrative, read-only diagnostics for persisted cross-domain references.

No customer HTTP endpoint, no write/repair action and no unscoped object payload.
Run only with authorized datacenter/operator database access.
"""

import json
from collections import Counter
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.actions.models import Action
from apps.ai_gateway.models import AISuggestion
from apps.common.domain_objects import inspect_domain_reference
from apps.documents.models import DocumentLink
from apps.evidence.models import EvidenceLink
from apps.workflows.models import WorkflowInstance


# Source, model, type field, target ID field, registry capability, parent field.
# DocumentLink currently validates any registered type (no capability marker).
REFERENCE_SOURCES = (
    ("action_source", Action, "source_type", "source_id", "action_source", None),
    ("ai_target", AISuggestion, "object_type", "object_id", "ai_target", None),
    ("document_link", DocumentLink, "object_type", "object_id", None, "document"),
    ("evidence_link", EvidenceLink, "object_type", "object_id", "evidence", "evidence"),
    ("workflow", WorkflowInstance, "object_type", "object_id", "workflow", "definition"),
)


def _parent_integrity(row, name):
    if name is None:
        return None
    parent = getattr(row, name)
    if parent.tenant_id != row.tenant_id:
        return "cross_tenant_source"
    if getattr(parent, "deleted_at", None) is not None:
        return "deleted_source"
    return None


def collect_domain_reference_findings(*, tenant_id=None):
    """Inspect active stored rows, returning sorted, deterministic metadata only."""
    findings = []
    checked = 0
    source_counts = {}
    for name, model, type_field, id_field, capability, parent in REFERENCE_SOURCES:
        qs = model._default_manager.all()
        if any(field.name == "deleted_at" for field in model._meta.fields):
            qs = qs.filter(deleted_at__isnull=True)
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        qs = qs.select_related("tenant", *( [parent] if parent else [] )).order_by("id")
        count = 0
        for row in qs.iterator(chunk_size=200):
            type_code = getattr(row, type_field, "") or ""
            target_id = getattr(row, id_field, None)
            if not type_code and target_id is None:
                continue  # Unbound Action/AI rows are intentional.
            checked += 1
            count += 1
            if not type_code or target_id is None:
                status = "incomplete_reference"
            else:
                status = _parent_integrity(row, parent) or inspect_domain_reference(
                    tenant=row.tenant, type_code=type_code,
                    object_id=target_id, capability=capability,
                )
                if status == "ok" and name == "workflow":
                    from apps.common.domain_objects import domain_object_scope, resolve_domain_object

                    target = resolve_domain_object(row.tenant, type_code, target_id)
                    scope = domain_object_scope(type_code, target)
                    if getattr(scope, "pk", None) != row.organization_unit_id:
                        status = "scope_mismatch"

            if status != "ok":
                findings.append({
                    "source": name,
                    "row_id": str(row.pk),
                    "tenant_id": str(row.tenant_id),
                    "type_code": str(type_code),
                    "object_id": str(target_id) if target_id else None,
                    "status": status,
                })
        source_counts[name] = count

    findings.sort(key=lambda f: (f["source"], f["tenant_id"], f["row_id"]))
    return {
        "schema": "grc-domain-reference-integrity-v1",
        "checked": checked,
        "ok": not findings,
        "by_source": source_counts,
        "by_status": dict(sorted(Counter(f["status"] for f in findings).items())),
        "findings": findings,
    }


class Command(BaseCommand):
    help = "Read-only integrity audit of cross-domain references; no repairs."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument(
            "--tenant-id", default=None, help="Limit the operator audit to one tenant UUID."
        )

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"]
        if tenant_id:
            try:
                tenant_id = UUID(tenant_id)
            except (ValueError, AttributeError, TypeError):
                raise CommandError("--tenant-id must be a valid UUID.") from None

        report = collect_domain_reference_findings(tenant_id=tenant_id)
        if options["as_json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(
                f"Checked {report['checked']} domain references; "
                f"{len(report['findings'])} finding(s)."
            )
            for finding in report["findings"]:
                self.stdout.write(
                    f"{finding['source']}:{finding['row_id']} "
                    f"{finding['type_code']}:{finding['object_id']} -> {finding['status']}"
                )

        if not report["ok"]:
            raise CommandError("Domain reference integrity check failed.")
