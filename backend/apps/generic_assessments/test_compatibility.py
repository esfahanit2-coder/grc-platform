import json
from io import StringIO
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.assessments.models import Assessment
from apps.frameworks.models import Framework, FrameworkVersion
from apps.generic_assessments.models import (
    AssessmentTemplate, AssessmentTemplateVersion, ComplianceAssessmentProfile, GenericAssessmentRun, TemplateCriterion,
)
from apps.generic_assessments.services import publish_template
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership


class AssessmentHistoryTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="compat-admin", password="StrongPassword123!")
        self.reviewer = User.objects.create_user(username="compat-reviewer", password="StrongPassword123!")
        self.tenant = Tenant.objects.create(name="Compatibility", code="compat")
        for user in (self.admin, self.reviewer):
            TenantMembership.objects.create(tenant=self.tenant, user=user, role_code="admin")
        self.scope = OrganizationUnit.objects.create(tenant=self.tenant, code="OPS", name="Operations", unit_type="department")
        self.hidden = OrganizationUnit.objects.create(tenant=self.tenant, code="HR", name="HR", unit_type="department")
        self.framework = Framework.objects.create(tenant=self.tenant, code="compat-fw", name="Compliance", status="active")
        self.version = FrameworkVersion.objects.create(framework=self.framework, version_code="2015", status="active")
        self.legacy = Assessment.objects.create(
            tenant=self.tenant, framework_version=self.version, organization_unit=self.scope,
            owner=self.admin, title="Legacy result", status="completed",
            overall_score=Decimal("65.000"), progress_percent=Decimal("100.000"),
        )
        template = AssessmentTemplate.objects.create(
            tenant=self.tenant, organization_unit=self.scope, code="BIA", title="BIA template", owner=self.admin,
        )
        version = AssessmentTemplateVersion.objects.create(template=template, version_code="1")
        TemplateCriterion.objects.create(version=version, code="A", title="Recovery readiness", response_type="boolean")
        version = publish_template(version=version, user=self.reviewer)
        self.generic = GenericAssessmentRun.objects.create(
            tenant=self.tenant, organization_unit=self.scope, template_version=version,
            owner=self.admin, title="Modern result",
        )
        self.other_legacy = Assessment.objects.create(
            tenant=self.tenant, framework_version=self.version, organization_unit=self.hidden,
            owner=self.admin, title="Confidential HR", status="draft",
        )
        self.headers = {"HTTP_X_TENANT_ID": str(self.tenant.id)}
        self.authenticate(self.admin)

    def authenticate(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")

    def get_history(self, query=""):
        return self.client.get("/api/v1/assessment-history/" + query, **self.headers)

    def test_union_is_read_only_and_preserves_legacy_score(self):
        before = (self.legacy.status, self.legacy.overall_score, self.legacy.progress_percent)
        response = self.get_history()
        self.assertEqual(response.status_code, 200, response.content)
        sources = {row["id"]: row for row in response.data["results"]}
        self.assertEqual(sources[str(self.legacy.id)]["source"], "legacy")
        self.assertEqual(sources[str(self.legacy.id)]["overall_score"], "65.000")
        self.assertEqual(sources[str(self.generic.id)]["source"], "generic")
        self.assertIsNone(sources[str(self.generic.id)]["overall_score"])
        self.legacy.refresh_from_db()
        self.assertEqual((self.legacy.status, self.legacy.overall_score, self.legacy.progress_percent), before)
        self.assertEqual(self.client.post("/api/v1/assessment-history/", {}, format="json", **self.headers).status_code, 405)

    def test_source_filter_global_paging_and_invalid_parameters(self):
        self.legacy.created_at = timezone.now() - timedelta(days=1)
        Assessment.objects.filter(pk=self.legacy.pk).update(created_at=self.legacy.created_at)
        top = self.get_history("?page_size=1")
        self.assertEqual(top.status_code, 200, top.content)
        self.assertTrue(top.data["has_more"])
        self.assertNotEqual(top.data["results"][0]["id"], str(self.legacy.id))
        second = self.get_history("?page_size=1&page=2")
        self.assertEqual(second.status_code, 200, second.content)
        only_generic = self.get_history("?source=generic")
        self.assertEqual(only_generic.status_code, 200)
        self.assertEqual([x["source"] for x in only_generic.data["results"]], ["generic"])
        for query in ("?page=0", "?page_size=101", "?source=unknown", "?organization_unit=not-a-uuid"):
            self.assertEqual(self.get_history(query).status_code, 400, query)

    def test_cross_tenant_isolation_and_scoped_read_permissions(self):
        foreign = Tenant.objects.create(name="Forbidden", code="compat-foreign")
        Framework.objects.create(tenant=foreign, code="foreign-fw", name="Foreign", status="active")
        user = get_user_model().objects.create_user(username="compat-foreign", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=foreign, user=user)
        fw = Framework.objects.get(tenant=foreign)
        fv = FrameworkVersion.objects.create(framework=fw, version_code="v1")
        foreign_record = Assessment.objects.create(
            tenant=foreign, framework_version=fv, owner=user, title="Other tenant result",
        )
        all_rows = self.get_history().data["results"]
        self.assertNotIn(str(foreign_record.id), {x["id"] for x in all_rows})
        scope_user = get_user_model().objects.create_user(username="compat-scoped", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=scope_user)
        roles = bootstrap_tenant_rbac(self.tenant)
        UserRoleScope.objects.create(tenant=self.tenant, user=scope_user, role=roles["compliance_manager"], organization_unit=self.scope)
        self.authenticate(scope_user)
        response = self.get_history()
        self.assertEqual(response.status_code, 200, response.content)
        ids = {x["id"] for x in response.data["results"]}
        self.assertEqual(ids, {str(self.generic.id), str(self.legacy.id)})
        self.assertNotIn(str(self.other_legacy.id), ids)
        self.assertEqual(self.get_history("?organization_unit=" + str(self.hidden.id)).data["results"], [])

    def test_backfill_reconciliation_plan_never_mutates_legacy(self):
        out = StringIO()
        profile = ComplianceAssessmentProfile.objects.create(
            tenant=self.tenant, framework_version=self.version,
            template_version=self.generic.template_version,
            title="Explicit, owner-reviewed candidate mapping",
        )
        old = (self.legacy.status, self.legacy.overall_score, self.legacy.progress_percent)
        call_command("assessment_backfill_plan", tenant_code=self.tenant.code, stdout=out)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["mode"], "dry-run")
        self.assertTrue(payload["read_only"])
        self.assertFalse(payload["execution_supported"])
        target = next(x for x in payload["rows"] if x["legacy_assessment_id"] == str(self.legacy.id))
        self.assertEqual(target["candidate_profile_ids"], [str(profile.id)])
        self.assertEqual(target["mapping_status"], "manual_review_required")
        self.assertTrue(target["completed_result_protected"])
        self.legacy.refresh_from_db()
        self.assertEqual((self.legacy.status, self.legacy.overall_score, self.legacy.progress_percent), old)
        with self.assertRaises(CommandError):
            call_command("assessment_backfill_plan", tenant_code="unknown-tenant", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("assessment_backfill_plan", tenant_code=self.tenant.code, limit=10001, stdout=StringIO())
