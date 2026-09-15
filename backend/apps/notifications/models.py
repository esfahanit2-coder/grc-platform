from django.conf import settings
from django.db import models
from apps.common.models import UUIDTimeStampedModel
from apps.tenancy.models import Tenant
class Notification(UUIDTimeStampedModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='notifications')
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='grc_notifications')
    category=models.CharField(max_length=60,default='general')
    title=models.CharField(max_length=255)
    body=models.TextField(blank=True)
    object_type=models.CharField(max_length=80,blank=True)
    object_id=models.UUIDField(null=True,blank=True)
    severity=models.CharField(max_length=20,default='info')
    read_at=models.DateTimeField(null=True,blank=True)
    metadata=models.JSONField(default=dict,blank=True)
    class Meta:indexes=[models.Index(fields=['tenant','user','read_at','created_at'])]
