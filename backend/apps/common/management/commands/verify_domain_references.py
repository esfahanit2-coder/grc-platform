import json

from django.core.management.base import BaseCommand, CommandError

from apps.actions.models import Action
from apps.ai_gateway.models import AISuggestion
from apps.documents.models import DocumentLink
from apps.evidence.models import EvidenceLink
from apps.workflows.models import WorkflowInstance

from apps.common.domain_registry import inspect_domain_reference


REFERENCE_SOURCES = (
    ("evidence_link", EvidenceLink, "object_type", "object_id", "tenant", "evidence_link"),
    ("document_link", DocumentLink, "object_type", "object_id", "tenant", "document_link"),
    ("action_source", Action, "source_type", "source_id", "tenant", "action_source"),
    ("workflow", WorkflowInstance, "object_type", "object_id", "tenant", "workflow"),
    ("ai_target", AISuggestion, "object_type", "object_id", "tenant", "ai_target"),
)


class Command(BaseCommand):
    help = "Verify cross-domain typed references without mutating application data."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        findings = []
        checked = 0

        for source_name, model, type_field, id_field, tenant_field, capability in REFERENCE_SOURCES:
            queryset = model._default_manager.all()
            if any(field.name == "deleted_at" for field in model._meta.fields):
                queryset = queryset.filter(deleted_at__isnull=True)

            for row in queryset.iterator():
                type_code = getattr(row, type_field, "") or ""
                object_id = getattr(row, id_field, None)
                if not type_code and not object_id:
                    continue
                checked += 1

                if bool(type_code) != bool(object_id):
                    findings.append(
                        {
                            "source": source_name,
                            "row_id": str(row.id),
                            "type_code": str(type_code),
                            "object_id": str(object_id) if object_id else None,
                            "status": "incomplete_reference",
                        }
                    )
                    continue

                tenant = getattr(row, tenant_field)
                result = inspect_domain_reference(
                    tenant=tenant,
                    type_code=type_code,
                    object_id=object_id,
                    capability=capability,
                )
                if result["status"] != "ok":
                    findings.append(
                        {
                            "source": source_name,
                            "row_id": str(row.id),
                            "type_code": str(type_code),
                            "object_id": str(object_id),
                            "status": result["status"],
                        }
                    )

        payload = {
            "schema": "grc-domain-reference-integrity-v1",
            "checked": checked,
            "findings": findings,
            "ok": not findings,
        }

        if options["as_json"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Checked {checked} domain references.")
                if not findings
                else self.style.ERROR(
                    f"Checked {checked} domain references; found {len(findings)} integrity issue(s)."
                )
            )
            for finding in findings:
                self.stdout.write(
                    f"{finding['source']}:{finding['row_id']} "
                    f"{finding['type_code']}:{finding['object_id']} -> {finding['status']}"
                )

        if findings:
            raise CommandError("Domain reference integrity check failed.")
