"""Read-only operator reconciliation plan; never copies or changes legacy answers."""
import json
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.utils import timezone

from apps.assessments.models import Assessment
from apps.generic_assessments.models import (
    AssessmentTemplateVersion, ComplianceAssessmentProfile,
)
from apps.tenancy.models import Tenant


class Command(BaseCommand):
    help = (
        "Create a tenant-scoped, read-only legacy-to-generic assessment mapping plan. "
        "This command never writes data or authorizes a backfill."
    )

    def add_arguments(self, parser):
        parser.add_argument("--tenant-code", required=True)
        parser.add_argument("--limit", default=500, type=int)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1 or limit > 10000:
            raise CommandError("--limit must be between 1 and 10000.")
        tenant = Tenant.objects.filter(
            code=options["tenant_code"], deleted_at__isnull=True,
        ).first()
        if tenant is None:
            raise CommandError("Tenant not found; refusing a cross-tenant scan.")

        # Resolve a proposed mapping only against published, tenant-owned
        # profiles referencing the *same* framework version and compatible scope.
        profiles = ComplianceAssessmentProfile.objects.filter(
            tenant=tenant, deleted_at__isnull=True,
            template_version__status=AssessmentTemplateVersion.Status.PUBLISHED,
            template_version__deleted_at__isnull=True,
            template_version__template__deleted_at__isnull=True,
        )
        records = Assessment.objects.filter(
            tenant=tenant, deleted_at__isnull=True,
        ).annotate(
            item_count=Count("items", filter=Q(items__deleted_at__isnull=True)),
        ).order_by("created_at", "id")[: limit + 1]

        rows = []
        for old in list(records)[:limit]:
            matches = profiles.filter(framework_version_id=old.framework_version_id)
            if old.organization_unit_id:
                matches = matches.filter(
                    Q(template_version__template__organization_unit_id=old.organization_unit_id) |
                    Q(template_version__template__organization_unit__isnull=True)
                )
            else:
                matches = matches.filter(template_version__template__organization_unit__isnull=True)
            candidate_ids = list(matches.values_list("id", flat=True)[:3])
            reason = (
                "no_published_mapping" if not candidate_ids else
                "ambiguous_mapping" if len(candidate_ids) > 1 else
                "manual_review_required"
            )
            rows.append({
                "legacy_assessment_id": str(old.id),
                "framework_version_id": str(old.framework_version_id),
                "organization_unit_id": str(old.organization_unit_id) if old.organization_unit_id else None,
                "status": old.status,
                "item_count": old.item_count,
                "candidate_profile_ids": [str(pk) for pk in candidate_ids],
                "mapping_status": reason,
                "completed_result_protected": old.status == Assessment.Status.COMPLETED,
            })

        payload = {
            "schema": "grc-generic-assessment-backfill-plan-v1",
            "tenant_code": tenant.code,
            "generated_at": timezone.now().isoformat(),
            "mode": "dry-run",
            "read_only": True,
            "execution_supported": False,
            "requires_owner_review": True,
            "rows": rows,
            "has_more": len(records) > limit,
        }
        self.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
