from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership
from .models import Document,DocumentVersion


class DocumentsSmokeTests(TestCase):
    def test_models_import(self):
        self.assertTrue(Document and DocumentVersion)


class DocumentExportSecurityTests(APITestCase):
    def setUp(self):
        User=get_user_model();self.user=User.objects.create_user(username='doc-admin',password='StrongPassword123!');self.tenant=Tenant.objects.create(name='Document Security',code='doc-security');TenantMembership.objects.create(tenant=self.tenant,user=self.user,role_code='admin')
        self.unit=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='HQ',name='HQ')
        self.document=Document.objects.create(tenant=self.tenant,organization_unit=self.unit,document_type='policy',code='POL-1',title='Policy',owner=self.user)
        self.version=DocumentVersion.objects.create(document=self.document,version='1.0',content='Controlled content',created_by=self.user)
        self.document.current_version=self.version;self.document.save(update_fields=['current_version','updated_at'])
        token=str(RefreshToken.for_user(self.user).access_token);self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}',HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_docx_export_creates_audit_event(self):
        response=self.client.get(f'/api/v1/document-versions/{self.version.id}/export/')
        self.assertEqual(response.status_code,200)
        self.assertTrue(AuditEvent.objects.filter(tenant=self.tenant,action='document.export',object_type='document_version',object_id=self.version.id).exists())
