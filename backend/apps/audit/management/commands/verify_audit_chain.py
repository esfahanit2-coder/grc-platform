import uuid

from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import verify_audit_chain
from apps.tenancy.models import Tenant


class Command(BaseCommand):
    help = "Verify the append-only audit hash chain for one tenant or for every audit stream."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            help="Verify only this tenant UUID. Omit to verify every tenant plus the global audit stream.",
        )

    def _verify_stream(self, tenant, label):
        result = verify_audit_chain(tenant)
        if not result["valid"]:
            raise CommandError(
                f"Audit chain FAILED for {label}: event={result.get('event_id')} "
                f"reason={result.get('reason')} checked={result.get('checked', 0)}"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Audit chain OK for {label}: checked={result['checked']} "
                f"last_hash={result.get('last_hash') or '[empty]'}"
            )
        )

    def handle(self, *args, **options):
        tenant_id = options.get("tenant_id")
        if tenant_id:
            try:
                parsed = uuid.UUID(str(tenant_id))
            except (TypeError, ValueError) as exc:
                raise CommandError("--tenant-id must be a valid UUID.") from exc
            tenant = Tenant.objects.filter(id=parsed).first()
            if not tenant:
                raise CommandError("Tenant not found.")
            self._verify_stream(tenant, f"tenant:{tenant.id}")
            return

        self._verify_stream(None, "global")
        for tenant in Tenant.objects.order_by("id").iterator():
            self._verify_stream(tenant, f"tenant:{tenant.id}")
