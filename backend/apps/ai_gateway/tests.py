from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant,TenantMembership
from .models import AIProviderConfig,KnowledgeChunk,AISuggestion
from .services import upsert_knowledge_chunk

User=get_user_model()

class AIGatewayScopeTests(APITestCase):
    def setUp(self):
        self.admin=User.objects.create_user(username='ai-admin',password='StrongPassword123!')
        self.user=User.objects.create_user(username='ai-scoped',password='StrongPassword123!')
        self.tenant=Tenant.objects.create(name='AI Tenant',code='ai-tenant')
        TenantMembership.objects.create(tenant=self.tenant,user=self.admin,role_code='admin')
        TenantMembership.objects.create(tenant=self.tenant,user=self.user,role_code='member')
        roles=bootstrap_tenant_rbac(self.tenant,admin_user=self.admin)
        self.a=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='A',name='A')
        self.b=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='B',name='B')
        UserRoleScope.objects.create(tenant=self.tenant,user=self.user,role=roles['risk_manager'],organization_unit=self.a)
        AIProviderConfig.objects.create(tenant=self.tenant,name='mock',provider_type='mock',model_name='mock',is_default=True)
        upsert_knowledge_chunk(tenant=self.tenant,organization_unit=self.a,source_type='risk',source_id=None,title='Allowed',content='privileged access risk in company A')
        upsert_knowledge_chunk(tenant=self.tenant,organization_unit=self.b,source_type='risk',source_id=None,title='Forbidden',content='secret vendor risk in company B')
        token=str(RefreshToken.for_user(self.user).access_token);self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}',HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_knowledge_list_is_scope_filtered(self):
        response=self.client.get('/api/v1/ai/knowledge/')
        self.assertEqual(response.status_code,200)
        titles={x['title'] for x in response.data['results']}
        self.assertIn('Allowed',titles);self.assertNotIn('Forbidden',titles)

    def test_rag_returns_only_authorized_sources_and_creates_auditable_interaction(self):
        response=self.client.post('/api/v1/ai/assist/rag/',{'query':'privileged access risk'},format='json')
        self.assertEqual(response.status_code,200)
        titles={x['title'] for x in response.data['sources']}
        self.assertIn('Allowed',titles);self.assertNotIn('Forbidden',titles)

    def test_ai_output_is_pending_suggestion_not_domain_write(self):
        response=self.client.post('/api/v1/ai/assist/document-draft/',{'title':'Access Policy','purpose':'draft only'},format='json')
        self.assertEqual(response.status_code,200)
        suggestion=AISuggestion.objects.get(id=response.data['suggestion']['id'])
        self.assertEqual(suggestion.status,'pending')
