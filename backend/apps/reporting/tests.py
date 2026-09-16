from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.documents.models import ReportTemplate
from apps.tenancy.models import Tenant, TenantMembership
from .template_engine import render_html, safe_report_url_fetcher


class ReportingSmokeTests(TestCase):
    def test_import(self):
        from .views import ManagementDashboardView
        self.assertTrue(ManagementDashboardView)

    def test_html_context_is_autoescaped(self):
        rendered=render_html('<p>{{ value }}</p>',{'value':'<script>alert(1)</script>'})
        self.assertNotIn('<script>',rendered)
        self.assertIn('&lt;script&gt;',rendered)

    def test_report_fetcher_blocks_network_and_local_files(self):
        for url in ('http://127.0.0.1/internal','https://example.invalid/asset','file:///etc/passwd'):
            with self.assertRaises(ValueError):
                safe_report_url_fetcher(url)


class ReportExportAuditTests(APITestCase):
    def setUp(self):
        User=get_user_model();self.user=User.objects.create_user(username='report-admin',password='StrongPassword123!');self.tenant=Tenant.objects.create(name='Report Tenant',code='report-tenant');TenantMembership.objects.create(tenant=self.tenant,user=self.user,role_code='admin')
        self.template=ReportTemplate.objects.create(tenant=self.tenant,template_type='custom',name='Safe Template',configuration={'html_template':'<h1>{{ title }}</h1>'})
        token=str(RefreshToken.for_user(self.user).access_token);self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}',HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_html_report_export_is_audited(self):
        response=self.client.post('/api/v1/reports/render-template/',{'template_id':str(self.template.id),'format':'html','context':{'title':'Executive'}},format='json')
        self.assertEqual(response.status_code,200)
        self.assertTrue(AuditEvent.objects.filter(tenant=self.tenant,action='report.export',object_type='report_template',object_id=self.template.id,outcome='success').exists())

    def test_unsupported_report_format_is_rejected(self):
        response=self.client.post('/api/v1/reports/render-template/',{'template_id':str(self.template.id),'format':'xml','context':{}},format='json')
        self.assertEqual(response.status_code,400)
