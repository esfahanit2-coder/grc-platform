from django.apps import apps
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.audit.services import record_audit_event
from apps.identity.services import require_tenant_permission, require_whole_tenant_permission
from .models import WorkflowEvent,WorkflowInstance

OBJECT_MODEL_MAP={
    'risk':('risks','Risk'),
    'assessment':('assessments','Assessment'),
    'finding':('findings','Finding'),
    'document':('documents','Document'),
    'action':('actions','Action'),
    'audit':('internal_audits','AuditEngagement'),
}

def object_scope(tenant,object_type,object_id):
    spec=OBJECT_MODEL_MAP.get(object_type)
    if not spec: return None
    model=apps.get_model(*spec)
    obj=model.objects.filter(id=object_id).first()
    if not obj: raise ValidationError('Workflow target object was not found.')
    if hasattr(obj,'tenant_id') and obj.tenant_id!=tenant.id: raise ValidationError('Workflow target belongs to another tenant.')
    return getattr(obj,'organization_unit',None)

def start_workflow(*,tenant,user,definition,object_type,object_id,request=None):
    if definition.tenant_id!=tenant.id or not definition.is_active: raise ValidationError('Invalid workflow definition.')
    if definition.object_type!=object_type: raise ValidationError('Workflow definition does not match object type.')
    initial=definition.states.filter(is_initial=True,deleted_at__isnull=True).first()
    if not initial: raise ValidationError('Workflow has no initial state.')
    unit=object_scope(tenant,object_type,object_id)
    require_tenant_permission(user,tenant,'workflow.start',unit) if unit else require_whole_tenant_permission(user,tenant,'workflow.start')
    instance,created=WorkflowInstance.objects.get_or_create(tenant=tenant,definition=definition,object_type=object_type,object_id=object_id,defaults={'organization_unit':unit,'current_state':initial,'started_by':user,'status':'active'})
    if created:
        WorkflowEvent.objects.create(instance=instance,to_state=initial,actor=user,comment='Workflow started')
        record_audit_event(user,tenant,'workflow.start','workflow_instance',instance.id,metadata={'object_type':object_type,'object_id':str(object_id)},request=request)
    return instance

@transaction.atomic
def transition_workflow(*,tenant,user,instance,transition,comment='',request=None):
    instance=WorkflowInstance.objects.select_for_update().select_related('current_state','organization_unit').get(id=instance.id,tenant=tenant)
    if instance.status!='active': raise ValidationError('Workflow is not active.')
    if transition.definition_id!=instance.definition_id or transition.from_state_id!=instance.current_state_id: raise ValidationError('Transition is not allowed from the current state.')
    code=transition.required_permission_code or 'workflow.transition'
    require_tenant_permission(user,tenant,code,instance.organization_unit) if instance.organization_unit else require_whole_tenant_permission(user,tenant,code)
    previous=instance.current_state
    instance.current_state=transition.to_state
    if transition.to_state.is_terminal: instance.status='completed'
    instance.save(update_fields=['current_state','status','updated_at'])
    event=WorkflowEvent.objects.create(instance=instance,transition=transition,from_state=previous,to_state=transition.to_state,actor=user,comment=comment)
    record_audit_event(user,tenant,'workflow.transition','workflow_instance',instance.id,metadata={'transition':transition.code,'from':previous.code,'to':transition.to_state.code},request=request)
    return instance,event
