from django.utils import timezone
from .models import Notification

def notify_user(*,tenant,user,title,body='',category='general',object_type='',object_id=None,severity='info',metadata=None):
    return Notification.objects.create(tenant=tenant,user=user,title=title,body=body,category=category,object_type=object_type,object_id=object_id,severity=severity,metadata=metadata or {})

def mark_read(notification):
    if not notification.read_at:
        notification.read_at=timezone.now();notification.save(update_fields=['read_at','updated_at'])
    return notification
