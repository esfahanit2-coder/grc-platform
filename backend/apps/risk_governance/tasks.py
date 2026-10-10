from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from apps.notifications.models import Notification
from apps.notifications.services import notify_user
from apps.tenancy.models import TenantMembership
from .models import RiskAcceptance


@shared_task(name="apps.risk_governance.tasks.create_risk_acceptance_review_notifications")
def create_risk_acceptance_review_notifications():
    today = timezone.localdate()
    due = today + timedelta(days=7)
    rows = RiskAcceptance.objects.filter(
        status=RiskAcceptance.Status.APPROVED,
        deleted_at__isnull=True,
        expires_on__gte=today,
    ).filter(review_on__lte=due).select_related("risk", "tenant", "requested_by")
    count = 0
    for decision in rows:
        if not TenantMembership.objects.filter(
            tenant=decision.tenant, user=decision.requested_by, is_active=True,
        ).exists():
            continue
        if Notification.objects.filter(
            tenant=decision.tenant, user=decision.requested_by,
            object_type="risk_acceptance", object_id=decision.id,
            category="risk_acceptance_review", created_at__date=today,
        ).exists():
            continue
        notify_user(
            tenant=decision.tenant, user=decision.requested_by,
            category="risk_acceptance_review",
            title=f"بازبینی پذیرش ریسک: {decision.risk.code}",
            body=f"تاریخ بازبینی: {decision.review_on} | انقضا: {decision.expires_on}",
            object_type="risk_acceptance", object_id=decision.id,
            severity="warning",
        )
        count += 1
    return count
