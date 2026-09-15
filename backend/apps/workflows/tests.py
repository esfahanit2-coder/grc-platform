from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from rest_framework.exceptions import PermissionDenied
from django.test import TestCase
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk,RiskCategory
from apps.tenancy.models import Tenant,TenantMembership
from .models import WorkflowDefinition,WorkflowState,WorkflowTransition
from .services import start_workflow,transition_workflow
User=get_user_model()

class WorkflowScopeTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user(username='wf-admin',password='StrongPassword123!');self.user=User.objects.create_user(username='wf-user',password='StrongPassword123!')
        self.tenant=Tenant.objects.create(name='WF',code='wf');TenantMembership.objects.create(tenant=self.tenant,user=self.admin,role_code='admin');TenantMembership.objects.create(tenant=self.tenant,user=self.user,role_code='member');roles=bootstrap_tenant_rbac(self.tenant,admin_user=self.admin)
        self.a=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='A',name='A');self.b=OrganizationUnit.objects.create(tenant=self.tenant,unit_type='company',code='B',name='B');UserRoleScope.objects.create(tenant=self.tenant,user=self.user,role=roles['risk_manager'],organization_unit=self.a)
        cat=RiskCategory.objects.create(tenant=self.tenant,code='cyber',name='Cyber');self.ra=Risk.objects.create(tenant=self.tenant,organization_unit=self.a,category=cat,code='RA',title='A risk',owner=self.user);self.rb=Risk.objects.create(tenant=self.tenant,organization_unit=self.b,category=cat,code='RB',title='B risk',owner=self.admin)
        self.definition=WorkflowDefinition.objects.create(tenant=self.tenant,name='Risk review',object_type='risk');self.draft=WorkflowState.objects.create(definition=self.definition,code='draft',name='Draft',is_initial=True);self.approved=WorkflowState.objects.create(definition=self.definition,code='approved',name='Approved',is_terminal=True);self.transition=WorkflowTransition.objects.create(definition=self.definition,code='approve',name='Approve',from_state=self.draft,to_state=self.approved,required_permission_code='risk.manage')
    def test_scoped_user_can_start_and_transition_own_unit_workflow(self):
        instance=start_workflow(tenant=self.tenant,user=self.user,definition=self.definition,object_type='risk',object_id=self.ra.id)
        instance,_=transition_workflow(tenant=self.tenant,user=self.user,instance=instance,transition=self.transition)
        self.assertEqual(instance.status,'completed')
    def test_scoped_user_cannot_start_sibling_workflow(self):
        with self.assertRaises(PermissionDenied):start_workflow(tenant=self.tenant,user=self.user,definition=self.definition,object_type='risk',object_id=self.rb.id)
