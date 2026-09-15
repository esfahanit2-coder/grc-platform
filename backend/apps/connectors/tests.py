from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.evidence.models import Evidence
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant,TenantMembership
from .clients import ConnectorResult
from .models import ConnectorConfig
from .services import run_connector
class ConnectorEvidenceTests(TestCase):
    def setUp(self):
        self.tenant=Tenant.objects.create(name="Pilot",code="pilot-connectors");self.user=get_user_model().objects.create_user(username="pilotconn",password="Password12345!");TenantMembership.objects.create(tenant=self.tenant,user=self.user,role_code="admin");self.unit=OrganizationUnit.objects.create(tenant=self.tenant,unit_type="company",code="HQ",name="HQ")
    @patch("apps.connectors.services.connector_for")
    def test_sync_creates_evidence(self,factory):
        cfg=ConnectorConfig.objects.create(tenant=self.tenant,organization_unit=self.unit,name="FG",connector_type="fortigate",base_url="https://fg.example",secret_env_var="FG_TOKEN")
        factory.return_value.collect.return_value=ConnectorResult("FortiGate snapshot",{"ok":True})
        run,evidence=run_connector(cfg,user=self.user)
        self.assertEqual(run.status,"succeeded");self.assertEqual(evidence.tenant,self.tenant);self.assertTrue(Evidence.objects.filter(id=evidence.id).exists())
