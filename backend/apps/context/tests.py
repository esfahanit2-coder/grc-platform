from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.domain_objects import domain_object_scope, resolve_domain_object
from apps.controls.models import Control, ControlImplementation
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.internal_audits.models import AuditEngagement
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk
from apps.tenancy.models import Tenant, TenantMembership
from .models import AuditProcess, BusinessProcess, ControlImplementationProcess, RiskProcess

User = get_user_model()

class BusinessProcessApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Process A", code="process-a")
        self.other_tenant = Tenant.objects.create(name="Process B", code="process-b")
        self.user = User.objects.create_user(username="process-admin", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=self.user, role_code="admin")
        self.unit = OrganizationUnit.objects.create(tenant=self.tenant, unit_type="department", code="UNIT", name="Unit")
        self.other_unit = OrganizationUnit.objects.create(tenant=self.tenant, unit_type="department", code="OTHER", name="Other")
        self.headers = {"HTTP_X_TENANT_ID": str(self.tenant.id)}
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}")

    def create_process(self, code="P1", unit=None, parent=None):
        return BusinessProcess.objects.create(tenant=self.tenant, organization_unit=unit or self.unit, code=code, name=code, owner=self.user, parent=parent)

    def test_process_create_and_cycles(self):
        r = self.client.post("/api/v1/business-processes/", {"code": "MAIN", "name": "Main", "owner": self.user.id, "organization_unit": str(self.unit.id), "criticality": 5}, format="json", **self.headers)
        self.assertEqual(r.status_code, 201, r.content)
        p = BusinessProcess.objects.get(pk=r.data["id"])
        child = self.create_process("CHILD", parent=p)
        cycle = self.client.patch(f"/api/v1/business-processes/{p.id}/", {"parent": str(child.id)}, format="json", **self.headers)
        self.assertEqual(cycle.status_code, 400)
        self.assertEqual(domain_object_scope("business_process", resolve_domain_object(self.tenant, "business_process", p.id)), self.unit)

    def test_links_risk_control_audit_and_scope(self):
        proc = self.create_process()
        risk = Risk.objects.create(tenant=self.tenant, organization_unit=self.unit, code="R1", title="R1", owner=self.user)
        control = Control.objects.create(tenant=self.tenant, code="C1", title="C1", created_by=self.user)
        impl = ControlImplementation.objects.create(tenant=self.tenant, control=control, organization_unit=self.unit, owner=self.user)
        audit = AuditEngagement.objects.create(tenant=self.tenant, organization_unit=self.unit, title="Audit", lead_auditor=self.user)
        scenarios = [
            ("/api/v1/risk-processes/", {"business_process": str(proc.id), "risk": str(risk.id)}, RiskProcess),
            ("/api/v1/control-processes/", {"business_process": str(proc.id), "control_implementation": str(impl.id)}, ControlImplementationProcess),
            ("/api/v1/audit-processes/", {"business_process": str(proc.id), "audit_engagement": str(audit.id)}, AuditProcess),
        ]
        for url, payload, model in scenarios:
            r = self.client.post(url, payload, format="json", **self.headers)
            self.assertEqual(r.status_code, 201, (url, r.content))
            self.assertTrue(model.objects.filter(tenant=self.tenant, business_process=proc).exists())
        self.assertEqual(self.client.delete(f"/api/v1/business-processes/{proc.id}/", **self.headers).status_code, 400)

    def test_mismatched_scope_and_tenant_do_not_link(self):
        proc = self.create_process()
        risk_other_unit = Risk.objects.create(tenant=self.tenant, organization_unit=self.other_unit, code="R2", title="R2", owner=self.user)
        mismatch = self.client.post("/api/v1/risk-processes/", {"business_process": str(proc.id), "risk": str(risk_other_unit.id)}, format="json", **self.headers)
        self.assertEqual(mismatch.status_code, 400)
        remote_owner = User.objects.create_user(username="foreign-owner", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.other_tenant, user=remote_owner)
        foreign_unit = OrganizationUnit.objects.create(tenant=self.other_tenant, unit_type="department", code="F", name="Foreign")
        foreign_process = BusinessProcess.objects.create(tenant=self.other_tenant, organization_unit=foreign_unit, code="FP", name="Remote", owner=remote_owner)
        foreign = self.client.post("/api/v1/risk-processes/", {"business_process": str(foreign_process.id), "risk": str(risk_other_unit.id)}, format="json", **self.headers)
        self.assertEqual(foreign.status_code, 400)
        self.assertIsNone(resolve_domain_object(self.tenant, "business_process", foreign_process.id))

    def test_scoped_permissions_and_link_read_filter(self):
        hidden = self.create_process("HIDDEN", unit=self.other_unit)
        visible = self.create_process("VISIBLE")
        risk = Risk.objects.create(tenant=self.tenant, organization_unit=self.other_unit, code="R-HIDDEN", title="Hidden", owner=self.user)
        RiskProcess.objects.create(tenant=self.tenant, business_process=hidden, risk=risk)
        user = User.objects.create_user(username="process-manager", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=user)
        roles = bootstrap_tenant_rbac(self.tenant)
        UserRoleScope.objects.create(tenant=self.tenant, user=user, role=roles["grc_manager"], organization_unit=self.unit)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        response = self.client.get("/api/v1/business-processes/", **self.headers)
        self.assertEqual({row["code"] for row in response.data["results"]}, {"VISIBLE"})
        self.assertEqual(self.client.get(f"/api/v1/business-processes/{hidden.id}/", **self.headers).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/risk-processes/", **self.headers).data["results"], [])
        self.assertEqual(self.client.delete(f"/api/v1/business-processes/{hidden.id}/", **self.headers).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/business-processes/", {"code": "BAD", "name": "bad", "owner": str(user.id), "organization_unit": str(self.other_unit.id)}, format="json", **self.headers).status_code, 403)
