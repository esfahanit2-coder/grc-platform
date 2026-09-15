from celery import shared_task
from django.utils import timezone
from apps.actions.models import Action
from .models import Notification

@shared_task
def create_overdue_action_notifications():
    today=timezone.localdate();created=0
    for action in Action.objects.filter(deleted_at__isnull=True,due_date__lt=today).exclude(status__in=[Action.Status.DONE,Action.Status.CANCELLED]).select_related('owner','tenant'):
        exists=Notification.objects.filter(tenant=action.tenant,user=action.owner,category='overdue_action',object_type='action',object_id=action.id,created_at__date=today).exists()
        if not exists:
            Notification.objects.create(tenant=action.tenant,user=action.owner,category='overdue_action',title=f'Overdue action: {action.title}',body=f'Due date: {action.due_date}',object_type='action',object_id=action.id,severity='warning');created+=1
    return created
