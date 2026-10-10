from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.assessments.models import Assessment, AssessmentItem
from apps.frameworks.models import Framework, FrameworkVersion, Requirement
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership
from .models import (
    ApplicabilityDecision, AssessmentTemplate, AssessmentTemplateVersion,
    GenericAssessmentItem, GenericAssessmentRun, TemplateCriterion,
)


User = get_user_model()


class GenericAssessmentCompatibilityTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Generic test", code="gen-a")
        self.foreign_tenant = Tenant.objects.create(name="Foreign", code="gen-b")
        self.author = User.objects.create_user(username="gen-author", password="StrongPassword123!")
        self.reviewer = User.objects.create_user(username="gen-reviewer", password="StrongPassword123!")
        for user in (self.author, self.reviewer):
            TenantMembership.objects.create(tenant=self.tenant, user=user, role_code="admin")
        self.unit = OrganizationUnit.objects.create(tenant=self.tenant, unit_type="department", code="A", name="Finance")
        self.other_unit = OrganizationUnit.objects.create(tenant=self.tenant, unit_type="department", code="B", name="HR")
        self.headers = {"HTTP_X_TENANT_ID": str(self.tenant.id)}
        self.login(self.author)
        self.framework = Framework.objects.create(tenant=self.tenant, code="legacy", name="Legacy", status="active")
        self.framework_version = FrameworkVersion.objects.create(framework=self.framework, version_code="2015", status="active")
        self.requirement = Requirement.objects.create(framework_version=self.framework_version, code="1.1", title="Old requirement")
        self.legacy = Assessment.objects.create(
            tenant=self.tenant, framework_version=self.framework_version, title="Old Assessment",
            organization_unit=self.unit, owner=self.author, status="completed",
        )
        self.legacy_item = AssessmentItem.objects.create(
            assessment=self.legacy, requirement=self.requirement,
            requirement_code_snapshot="1.1", requirement_title_snapshot="Old requirement",
            status="compliant", applicability="applicable", score=100,
        )

    def login(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")

    def api(self, path, data=None, method="post"):
        return getattr(self.client, method)(path, data or {}, format="json", **self.headers)

    def make_template(self):
        r = self.api("/api/v1/assessment-templates/", {
            "organization_unit": str(self.unit.id), "code": "BIA",
            "title": "Business impact", "owner": self.author.id,
        })
        self.assertEqual(r.status_code, 201, r.content)
        tid = r.data["id"]
        v = self.api("/api/v1/assessment-template-versions/", {
            "template": str(tid), "version_code": "v1",
        })
        self.assertEqual(v.status_code, 201, v.content)
        return v.data["id"]

    def make_published(self, response_type="boolean", choices=None):
        version = self.make_template()
        r = self.api("/api/v1/assessment-criteria/", {
            "version": str(version), "code": "A1", "title": "Availability",
            "response_type": response_type, "choices": choices or [],
            "weight": "2.000", "applicability_mode": "review",
        })
        self.assertEqual(r.status_code, 201, r.content)
        self.login(self.author)
        denied = self.api(f"/api/v1/assessment-template-versions/{version}/publish/")
        self.assertEqual(denied.status_code, 400)
        self.login(self.reviewer)
        good = self.api(f"/api/v1/assessment-template-versions/{version}/publish/")
        self.assertEqual(good.status_code, 200, good.content)
        self.login(self.author)
        return version, r.data["id"]

    def make_run(self, version):
        r = self.api("/api/v1/generic-assessments/", {
            "template_version": str(version), "title": "BIA pilot",
            "organization_unit": str(self.unit.id), "owner": self.author.id,
        })
        self.assertEqual(r.status_code, 201, r.content)
        return r.data["id"]

    def test_published_versions_freeze_criteria_and_snapshot(self):
        version, criterion = self.make_published()
        denied = self.api("/api/v1/assessment-criteria/", {
            "version": str(version), "code": "B2", "title": "Invalid", "response_type": "text",
        })
        self.assertEqual(denied.status_code, 400)
        run = self.make_run(version)
        item = GenericAssessmentItem.objects.get(run_id=run)
        self.assertEqual(item.criterion_code_snapshot, "A1")
        self.assertEqual(item.weight_snapshot, 2)
        self.assertEqual(item.applicability_mode_snapshot, "review")
        self.assertEqual(str(GenericAssessmentRun.objects.get(pk=run).template_version_id), str(version))

    def test_answer_validation_review_and_completion(self):
        version, _ = self.make_published(response_type="number")
        run_id = self.make_run(version)
        item = GenericAssessmentItem.objects.get(run_id=run_id)
        denied = self.api(f"/api/v1/generic-assessment-items/{item.id}/answer/", {"value": 201})
        self.assertEqual(denied.status_code, 400)
        good = self.api(f"/api/v1/generic-assessment-items/{item.id}/answer/", {"value": "75.5"})
        self.assertEqual(good.status_code, 200, good.content)
        self.assertEqual(good.data["score_percent"], "75.500")
        blocked = self.api(f"/api/v1/generic-assessments/{run_id}/complete/")
        self.assertEqual(blocked.status_code, 400)
        proposal = self.api("/api/v1/assessment-applicability-decisions/", {
            "generic_item": str(item.id), "decision": "applicable", "rationale": "Critical control.",
        })
        self.assertEqual(proposal.status_code, 201, proposal.content)
        denied_review = self.api(f"/api/v1/assessment-applicability-decisions/{proposal.data['id']}/review/")
        self.assertEqual(denied_review.status_code, 403)
        self.login(self.reviewer)
        review = self.api(f"/api/v1/assessment-applicability-decisions/{proposal.data['id']}/review/")
        self.assertEqual(review.status_code, 200, review.content)
        completed = self.api(f"/api/v1/generic-assessments/{run_id}/complete/")
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertEqual(completed.data["summary"]["score_percent"], "75.500")
        self.login(self.author)
        immutable = self.api(f"/api/v1/generic-assessment-items/{item.id}/answer/", {"value": 10})
        self.assertEqual(immutable.status_code, 400)

    def test_legacy_completed_assessment_is_not_changed_by_new_applicability(self):
        old_status, old_score = self.legacy_item.status, self.legacy_item.score
        response = self.api("/api/v1/assessment-applicability-decisions/", {
            "legacy_item": str(self.legacy_item.id), "decision": "not_applicable",
            "rationale": "Separate governance proposal with no legacy mutation.",
        })
        self.assertEqual(response.status_code, 201, response.content)
        self.legacy_item.refresh_from_db()
        self.assertEqual((self.legacy_item.status, self.legacy_item.score), (old_status, old_score))
        self.assertEqual(Assessment.objects.get(pk=self.legacy.id).status, "completed")
        self.login(self.reviewer)
        reviewed = self.api(f"/api/v1/assessment-applicability-decisions/{response.data['id']}/review/")
        self.assertEqual(reviewed.status_code, 200, reviewed.content)
        self.legacy_item.refresh_from_db()
        self.assertEqual((self.legacy_item.status, self.legacy_item.score), (old_status, old_score))

    def test_cross_tenant_and_organization_unit_scope(self):
        foreign_user = User.objects.create_user(username="gen-foreign", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.foreign_tenant, user=foreign_user)
        foreign_template = AssessmentTemplate.objects.create(
            tenant=self.foreign_tenant, code="FOR", title="Foreign", owner=foreign_user,
        )
        invalid = self.api("/api/v1/assessment-template-versions/", {
            "template": str(foreign_template.id), "version_code": "v1",
        })
        self.assertEqual(invalid.status_code, 400)
        version = self.make_template()
        scoped = User.objects.create_user(username="gen-scoped", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=scoped)
        roles = bootstrap_tenant_rbac(self.tenant)
        UserRoleScope.objects.create(tenant=self.tenant, user=scoped, role=roles["compliance_manager"], organization_unit=self.other_unit)
        self.login(scoped)
        q = self.client.get("/api/v1/assessment-template-versions/", **self.headers)
        self.assertEqual(q.status_code, 200)
        self.assertEqual(len(q.data["results"]), 0)
        denied = self.api("/api/v1/generic-assessments/", {
            "template_version": str(version), "title": "IDOR", "owner": scoped.id,
            "organization_unit": str(self.other_unit.id),
        })
        self.assertIn(denied.status_code, (400, 403))


    def test_always_applicable_item_can_complete_without_separate_applicability_decision(self):
        version = self.make_template()
        criterion = self.api("/api/v1/assessment-criteria/", {
            "version": str(version), "code": "ALWAYS", "title": "Always applicable",
            "response_type": "boolean", "required": True, "applicability_mode": "always",
        })
        self.assertEqual(criterion.status_code, 201, criterion.content)
        self.login(self.reviewer)
        published = self.api(f"/api/v1/assessment-template-versions/{version}/publish/")
        self.assertEqual(published.status_code, 200, published.content)
        self.login(self.author)
        run_id = self.make_run(version)
        item = GenericAssessmentItem.objects.get(run_id=run_id)
        answered = self.api(f"/api/v1/generic-assessment-items/{item.id}/answer/", {"value": False})
        self.assertEqual(answered.status_code, 200, answered.content)
        self.login(self.reviewer)
        completed = self.api(f"/api/v1/generic-assessments/{run_id}/complete/")
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertEqual(completed.data["summary"]["score_percent"], "0.000")

    def test_choice_type_is_strict(self):
        version, _ = self.make_published("choice", ["yes", "no"])
        run = self.make_run(version)
        item = GenericAssessmentItem.objects.get(run_id=run)
        self.assertEqual(self.api(f"/api/v1/generic-assessment-items/{item.id}/answer/", {"value": "other"}).status_code, 400)
        self.assertEqual(self.api(f"/api/v1/generic-assessment-items/{item.id}/answer/", {"value": "yes"}).status_code, 200)
