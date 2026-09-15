from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.assessments.models import Assessment, AssessmentItem
from apps.frameworks.models import Framework, FrameworkVersion, Requirement
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership
from .models import Evidence, EvidenceLink

User=get_user_model()

class EvidenceTests(APITestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='evidence-admin',password='StrongPassword123!');self.tenant=Tenant.objects.create(name='Tenant A',code='evidence-a');TenantMembership.objects.create(tenant=self.tenant,user=self.user,role_code='admin')
        self.unit=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='A',name='Company A',manager=self.user);self.other_unit=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='B',name='Company B',manager=self.user)
        fw=Framework.objects.create(tenant=self.tenant,code='ev-fw',name='Evidence FW',status='active');ver=FrameworkVersion.objects.create(framework=fw,version_code='1',status='active',is_locked=True);req1=Requirement.objects.create(framework_version=ver,code='1',title='One');req2=Requirement.objects.create(framework_version=ver,code='2',title='Two')
        self.assessment=Assessment.objects.create(tenant=self.tenant,framework_version=ver,organization_unit=self.unit,title='A',owner=self.user,status='in_progress')
        self.item1=AssessmentItem.objects.create(assessment=self.assessment,requirement=req1,requirement_code_snapshot='1',requirement_title_snapshot='One');self.item2=AssessmentItem.objects.create(assessment=self.assessment,requirement=req2,requirement_code_snapshot='2',requirement_title_snapshot='Two')
        self.evidence=Evidence.objects.create(tenant=self.tenant,organization_unit=self.unit,title='Policy',evidence_type='text',text_content='approved',owner=self.user)
        token=str(RefreshToken.for_user(self.user).access_token);self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}');self.headers={'HTTP_X_TENANT_ID':str(self.tenant.id)}

    def test_same_evidence_can_support_multiple_assessment_items(self):
        for item in (self.item1,self.item2):
            r=self.client.post('/api/v1/evidence-links/',{'evidence':str(self.evidence.id),'object_type':'assessment_item','object_id':str(item.id),'relation_type':'proves'},format='json',**self.headers);self.assertEqual(r.status_code,201)
        self.assertEqual(EvidenceLink.objects.filter(evidence=self.evidence).count(),2)

    def test_scoped_evidence_cannot_link_across_units(self):
        other_assessment=Assessment.objects.create(tenant=self.tenant,framework_version=self.assessment.framework_version,organization_unit=self.other_unit,title='B',owner=self.user,status='in_progress')
        other_item=AssessmentItem.objects.create(assessment=other_assessment,requirement=self.item1.requirement,requirement_code_snapshot='1',requirement_title_snapshot='One')
        r=self.client.post('/api/v1/evidence-links/',{'evidence':str(self.evidence.id),'object_type':'assessment_item','object_id':str(other_item.id)},format='json',**self.headers)
        self.assertEqual(r.status_code,400)
