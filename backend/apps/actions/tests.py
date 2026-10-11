from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant,TenantMembership
from .models import Action
User=get_user_model()
class ActionTests(APITestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='action-admin',password='StrongPassword123!');self.tenant=Tenant.objects.create(name='Tenant A',code='action-a');TenantMembership.objects.create(tenant=self.tenant,user=self.user,role_code='admin');self.unit=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='A',name='A',manager=self.user);token=str(RefreshToken.for_user(self.user).access_token);self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}');self.headers={'HTTP_X_TENANT_ID':str(self.tenant.id)}
    def test_done_action_sets_progress_and_completion(self):
        a=Action.objects.create(tenant=self.tenant,organization_unit=self.unit,title='Task',owner=self.user);r=self.client.patch(f'/api/v1/actions/{a.id}/',{'status':'done'},format='json',**self.headers);self.assertEqual(r.status_code,200);a.refresh_from_db();self.assertEqual(a.progress,100);self.assertIsNotNone(a.completed_at)

    def test_source_risk_treatment_rejects_foreign_tenant_and_accepts_local(self):
        from apps.risks.models import Risk, RiskTreatment

        own_risk = Risk.objects.create(
            tenant=self.tenant, organization_unit=self.unit,
            code="ACTION-R1", title="Own risk", owner=self.user,
        )
        own_treatment = RiskTreatment.objects.create(
            risk=own_risk, strategy="reduce", owner=self.user,
        )
        foreign_tenant = Tenant.objects.create(name="Foreign action tenant", code="action-foreign")
        foreign_unit = OrganizationUnit.objects.create(
            tenant=foreign_tenant, unit_type="company", code="FOREIGN", name="Foreign"
        )
        foreign_risk = Risk.objects.create(
            tenant=foreign_tenant, organization_unit=foreign_unit,
            code="ACTION-OTHER", title="Other risk", owner=self.user,
        )
        foreign_treatment = RiskTreatment.objects.create(
            risk=foreign_risk, strategy="reduce", owner=self.user,
        )

        payload = {
            "organization_unit": str(self.unit.id),
            "title": "Linked action",
            "owner": self.user.id,
            "source_type": "risk_treatment",
            "source_id": str(foreign_treatment.id),
        }
        denied = self.client.post("/api/v1/actions/", payload, format="json", **self.headers)
        self.assertEqual(denied.status_code, 400)
        self.assertFalse(Action.objects.filter(source_id=foreign_treatment.id).exists())

        payload["source_id"] = str(own_treatment.id)
        allowed = self.client.post("/api/v1/actions/", payload, format="json", **self.headers)
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(str(Action.objects.get(id=allowed.data["id"]).source_id), str(own_treatment.id))

        payload["source_type"] = "not_registered"
        invalid_type = self.client.post("/api/v1/actions/", payload, format="json", **self.headers)
        self.assertEqual(invalid_type.status_code, 400)
