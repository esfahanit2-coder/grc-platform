from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.notifications.models import Notification
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk, RiskEvaluation, RiskMethodology
from apps.tenancy.models import Tenant, TenantMembership
from .models import RiskAcceptance, RiskAppetiteStatement, RiskTolerance
from .tasks import create_risk_acceptance_review_notifications

User = get_user_model()


class RiskGovernanceTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Governance A", code="gov-a")
        self.other = Tenant.objects.create(name="Governance B", code="gov-b")
        self.requester = User.objects.create_user(username="gov-requester", password="StrongPassword123!")
        self.approver = User.objects.create_user(username="gov-approver", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=self.requester, role_code="admin")
        TenantMembership.objects.create(tenant=self.tenant, user=self.approver, role_code="admin")
        self.unit = OrganizationUnit.objects.create(tenant=self.tenant, unit_type="department", code="U", name="Unit")
        self.hidden_unit = OrganizationUnit.objects.create(tenant=self.tenant, unit_type="department", code="H", name="Hidden")
        self.risk = Risk.objects.create(tenant=self.tenant, organization_unit=self.unit, code="R001", title="Demo", owner=self.requester)
        self.method = RiskMethodology.objects.create(tenant=self.tenant, name="Five level")
        self.evaluation = RiskEvaluation.objects.create(
            risk=self.risk, methodology=self.method, evaluation_type="residual",
            likelihood=Decimal("2"), impact=Decimal("4"), score=Decimal("8"), level="medium",
            evaluated_by=self.requester,
        )
        self.headers = {"HTTP_X_TENANT_ID": str(self.tenant.id)}
        self.authenticate(self.requester)

    def authenticate(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")

    def build_policy(self, maximum="10.0"):
        r = self.client.post("/api/v1/risk-appetites/", {
            "organization_unit": str(self.unit.id), "code": "ORG-SEC", "version": 1,
            "title": "Risk appetite", "owner": self.requester.id,
            "effective_from": str(timezone.localdate() - timedelta(days=1)),
            "effective_until": str(timezone.localdate() + timedelta(days=90)),
        }, format="json", **self.headers)
        self.assertEqual(r.status_code, 201, r.content)
        policy_id = r.data["id"]
        r = self.client.post("/api/v1/risk-tolerances/", {
            "statement": str(policy_id), "evaluation_type": "residual", "maximum_score": maximum,
        }, format="json", **self.headers)
        self.assertEqual(r.status_code, 201, r.content)
        self.authenticate(self.approver)
        r = self.client.post(f"/api/v1/risk-appetites/{policy_id}/approve/", {}, format="json", **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        self.authenticate(self.requester)
        return RiskAppetiteStatement.objects.get(pk=policy_id)

    def request_acceptance(self, policy, *, evaluation=None, supersedes=None, justification=""):
        values = {
            "risk": str(self.risk.id), "evaluation": str((evaluation or self.evaluation).id),
            "appetite": str(policy.id), "rationale": "Executive approved operating context.",
            "review_on": str(timezone.localdate() + timedelta(days=3)),
            "expires_on": str(timezone.localdate() + timedelta(days=30)),
            "exception_justification": justification,
        }
        if supersedes:
            values["supersedes"] = str(supersedes.id)
        r = self.client.post("/api/v1/risk-acceptances/", values, format="json", **self.headers)
        self.assertEqual(r.status_code, 201, r.content)
        return RiskAcceptance.objects.get(pk=r.data["id"])

    def test_appetite_requires_independent_approver_and_locks_version(self):
        policy = RiskAppetiteStatement.objects.create(
            tenant=self.tenant, organization_unit=self.unit, code="INDEPENDENT",
            title="Independent approval", owner=self.requester,
            effective_from=timezone.localdate(),
        )
        RiskTolerance.objects.create(statement=policy, evaluation_type="residual", maximum_score=Decimal("12"))
        r = self.client.post(f"/api/v1/risk-appetites/{policy.id}/approve/", {}, format="json", **self.headers)
        self.assertEqual(r.status_code, 403, r.content)
        self.authenticate(self.approver)
        r = self.client.post(f"/api/v1/risk-appetites/{policy.id}/approve/", {}, format="json", **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        r = self.client.patch(f"/api/v1/risk-appetites/{policy.id}/", {"title": "tampered"}, format="json", **self.headers)
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/v1/risk-tolerances/", {
            "statement": str(policy.id), "evaluation_type": "current", "maximum_score": "9.0"
        }, format="json", **self.headers)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(AuditEvent.objects.filter(tenant=self.tenant, action="risk_appetite.approve").exists())

    def test_acceptance_snapshot_independence_and_reminders(self):
        policy = self.build_policy()
        acceptance = self.request_acceptance(policy)
        self.assertEqual(acceptance.score_snapshot, Decimal("8"))
        self.authenticate(self.requester)
        denied = self.client.post(f"/api/v1/risk-acceptances/{acceptance.id}/approve/", {}, format="json", **self.headers)
        self.assertEqual(denied.status_code, 403)
        self.authenticate(self.approver)
        approved = self.client.post(f"/api/v1/risk-acceptances/{acceptance.id}/approve/", {
            "decision_note": "Within approved threshold."
        }, format="json", **self.headers)
        self.assertEqual(approved.status_code, 200, approved.content)
        self.assertTrue(approved.data["is_current"])
        self.evaluation.score = Decimal("21")
        self.evaluation.save(update_fields=["score", "updated_at"])
        acceptance.refresh_from_db()
        self.assertEqual(acceptance.score_snapshot, Decimal("8"))
        self.assertEqual(create_risk_acceptance_review_notifications(), 1)
        self.assertEqual(create_risk_acceptance_review_notifications(), 0)
        self.assertEqual(Notification.objects.filter(category="risk_acceptance_review", object_id=acceptance.id).count(), 1)

    def test_above_tolerance_requires_override_permission_and_justification(self):
        policy = self.build_policy(maximum="6")
        decision = self.request_acceptance(policy, justification="Continuity exception signed separately.")
        self.assertTrue(decision.exceeds_tolerance)
        limited = User.objects.create_user(username="governance-manager", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=limited)
        roles = bootstrap_tenant_rbac(self.tenant)
        UserRoleScope.objects.create(tenant=self.tenant, user=limited, role=roles["grc_manager"], organization_unit=self.unit)
        self.authenticate(limited)
        denied = self.client.post(f"/api/v1/risk-acceptances/{decision.id}/approve/", {
            "decision_note": "Escalated exception reviewed."
        }, format="json", **self.headers)
        self.assertEqual(denied.status_code, 403, denied.content)
        self.authenticate(self.approver)
        approved = self.client.post(f"/api/v1/risk-acceptances/{decision.id}/approve/", {
            "decision_note": "Exception accepted by senior approver."
        }, format="json", **self.headers)
        self.assertEqual(approved.status_code, 200, approved.content)
        self.assertTrue(approved.data["exceeds_tolerance"])

    def test_supersession_retains_historical_decision(self):
        policy = self.build_policy()
        first = self.request_acceptance(policy)
        self.authenticate(self.approver)
        self.assertEqual(self.client.post(f"/api/v1/risk-acceptances/{first.id}/approve/", {}, format="json", **self.headers).status_code, 200)
        self.authenticate(self.requester)
        newer_evaluation = RiskEvaluation.objects.create(
            risk=self.risk, methodology=self.method, evaluation_type="residual",
            likelihood=Decimal("2"), impact=Decimal("3"), score=Decimal("6"),
            level="medium", evaluated_by=self.requester,
        )
        second = self.request_acceptance(policy, evaluation=newer_evaluation, supersedes=first)
        self.authenticate(self.approver)
        approved = self.client.post(f"/api/v1/risk-acceptances/{second.id}/approve/", {}, format="json", **self.headers)
        self.assertEqual(approved.status_code, 200, approved.content)
        first.refresh_from_db()
        self.assertEqual(first.status, RiskAcceptance.Status.SUPERSEDED)
        self.assertEqual(first.score_snapshot, Decimal("8"))
        self.assertEqual(second.score_snapshot, Decimal("6"))

    def test_cross_tenant_and_cross_scope_idor(self):
        policy = self.build_policy()
        foreign_user = User.objects.create_user(username="gov-foreign", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.other, user=foreign_user)
        foreign_unit = OrganizationUnit.objects.create(tenant=self.other, unit_type="department", code="FOREIGN", name="Other")
        foreign_risk = Risk.objects.create(tenant=self.other, organization_unit=foreign_unit, code="FR", title="Foreign", owner=foreign_user)
        bad = self.client.post("/api/v1/risk-acceptances/", {
            "risk": str(foreign_risk.id), "evaluation": str(self.evaluation.id), "appetite": str(policy.id),
            "rationale": "bad", "review_on": str(timezone.localdate()),
            "expires_on": str(timezone.localdate() + timedelta(days=1)),
        }, format="json", **self.headers)
        self.assertEqual(bad.status_code, 400)
        other_risk = Risk.objects.create(tenant=self.tenant, organization_unit=self.hidden_unit, code="RH", title="Hidden", owner=self.requester)
        other_eval = RiskEvaluation.objects.create(
            risk=other_risk, methodology=self.method, evaluation_type="residual",
            likelihood=1, impact=1, score=1, level="low", evaluated_by=self.requester,
        )
        scoped = User.objects.create_user(username="gov-scoped", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=scoped)
        roles = bootstrap_tenant_rbac(self.tenant)
        UserRoleScope.objects.create(tenant=self.tenant, user=scoped, role=roles["risk_manager"], organization_unit=self.unit)
        self.authenticate(scoped)
        mismatch = self.client.post("/api/v1/risk-acceptances/", {
            "risk": str(other_risk.id), "evaluation": str(other_eval.id), "appetite": str(policy.id),
            "rationale": "bad", "review_on": str(timezone.localdate()),
            "expires_on": str(timezone.localdate() + timedelta(days=1)),
        }, format="json", **self.headers)
        self.assertIn(mismatch.status_code, (400, 403))
        listing = self.client.get("/api/v1/risk-appetites/", **self.headers)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["results"]), 1)

    def test_expired_request_rejected(self):
        policy = self.build_policy()
        resp = self.client.post("/api/v1/risk-acceptances/", {
            "risk": str(self.risk.id), "evaluation": str(self.evaluation.id),
            "appetite": str(policy.id), "rationale": "Outdated",
            "review_on": str(timezone.localdate() - timedelta(days=1)),
            "expires_on": str(timezone.localdate() - timedelta(days=1)),
        }, format="json", **self.headers)
        self.assertEqual(resp.status_code, 400)
