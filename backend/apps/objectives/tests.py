from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.common.domain_objects import domain_object_scope, resolve_domain_object
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk
from apps.tenancy.models import Tenant, TenantMembership
from .models import Objective, RiskObjective

User = get_user_model()

class ObjectiveApiTests(APITestCase):
    def setUp(self):
        self.a = Tenant.objects.create(name="A", code="obj-a")
        self.b = Tenant.objects.create(name="B", code="obj-b")
        self.user = User.objects.create_user(username="obj-admin", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.a, user=self.user, role_code="admin")
        self.unit = OrganizationUnit.objects.create(tenant=self.a, unit_type="department", code="SEC", name="Security")
        self.other_unit = OrganizationUnit.objects.create(tenant=self.a, unit_type="department", code="FIN", name="Finance")
        self.foreign = OrganizationUnit.objects.create(tenant=self.b, unit_type="department", code="FOREIGN", name="Foreign")
        self.headers = {"HTTP_X_TENANT_ID": str(self.a.id)}
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}")

    def make_objective(self, code="GOAL", parent=None, unit=None):
        return Objective.objects.create(
            tenant=self.a, organization_unit=unit or self.unit, parent=parent,
            code=code, title=code, owner=self.user
        )

    def test_create_update_and_audit(self):
        response = self.client.post("/api/v1/objectives/", {"code": "G1", "title": "Security", "owner": self.user.id, "organization_unit": str(self.unit.id)}, format="json", **self.headers)
        self.assertEqual(response.status_code, 201, response.content)
        ident = response.data["id"]
        edited = self.client.patch(f"/api/v1/objectives/{ident}/", {"status": "active"}, format="json", **self.headers)
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertTrue(AuditEvent.objects.filter(tenant=self.a, action="objective.create", object_id=ident).exists())
        self.assertTrue(AuditEvent.objects.filter(tenant=self.a, action="objective.update", object_id=ident).exists())

    def test_cross_tenant_parent_and_scope_rejected(self):
        foreign_owner = User.objects.create_user(username="obj-foreign", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.b, user=foreign_owner)
        foreign_parent = Objective.objects.create(tenant=self.b, organization_unit=self.foreign, code="F1", title="Foreign", owner=foreign_owner)
        payload = {"code": "NEW", "title": "New", "owner": self.user.id, "organization_unit": str(self.unit.id), "parent": str(foreign_parent.id)}
        self.assertEqual(self.client.post("/api/v1/objectives/", payload, format="json", **self.headers).status_code, 400)
        payload["parent"] = None
        payload["organization_unit"] = str(self.foreign.id)
        self.assertEqual(self.client.post("/api/v1/objectives/", payload, format="json", **self.headers).status_code, 400)

    def test_cycle_rejected_and_cross_scope_parent_rejected(self):
        parent = self.make_objective("P")
        child = self.make_objective("C", parent)
        self.assertEqual(self.client.patch(f"/api/v1/objectives/{parent.id}/", {"parent": str(child.id)}, format="json", **self.headers).status_code, 400)
        other_scope = self.make_objective("OTHER", unit=self.other_unit)
        self.assertEqual(self.client.patch(f"/api/v1/objectives/{child.id}/", {"parent": str(other_scope.id)}, format="json", **self.headers).status_code, 400)

    def test_link_to_risk_and_registry_resolution(self):
        objective = self.make_objective()
        risk = Risk.objects.create(tenant=self.a, organization_unit=self.unit, code="R1", title="R1", owner=self.user)
        result = self.client.post("/api/v1/risk-objectives/", {"risk": str(risk.id), "objective": str(objective.id), "relationship_type": "threatens"}, format="json", **self.headers)
        self.assertEqual(result.status_code, 201, result.content)
        self.assertTrue(RiskObjective.objects.filter(tenant=self.a, risk=risk, objective=objective).exists())
        obj = resolve_domain_object(self.a, "objective", objective.id)
        self.assertEqual(domain_object_scope("objective", obj), self.unit)
        self.assertEqual(self.client.delete(f"/api/v1/objectives/{objective.id}/", **self.headers).status_code, 400)

    def test_scoped_user_cannot_read_other_unit_or_write_its_links(self):
        first = self.make_objective("ONE")
        second = self.make_objective("TWO", unit=self.other_unit)
        manager = User.objects.create_user(username="obj-scoped", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.a, user=manager)
        roles = bootstrap_tenant_rbac(self.a)
        UserRoleScope.objects.create(tenant=self.a, user=manager, role=roles["grc_manager"], organization_unit=self.unit)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(manager).access_token}")
        response = self.client.get("/api/v1/objectives/", **self.headers)
        self.assertEqual({row["code"] for row in response.data["results"]}, {"ONE"})
        self.assertEqual(self.client.get(f"/api/v1/objectives/{second.id}/", **self.headers).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/v1/objectives/{second.id}/", {"title": "hidden"}, format="json", **self.headers).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/objectives/{second.id}/", **self.headers).status_code, 404)
        risk = Risk.objects.create(tenant=self.a, organization_unit=self.other_unit, code="R-OTHER", title="Other", owner=self.user)
        link = self.client.post("/api/v1/risk-objectives/", {"objective": str(first.id), "risk": str(risk.id)}, format="json", **self.headers)
        self.assertEqual(link.status_code, 400)

    def test_direct_model_validation(self):
        obj = self.make_objective("ROOT")
        obj.parent = obj
        with self.assertRaises(ValidationError):
            obj.save()
