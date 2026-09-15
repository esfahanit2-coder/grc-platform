from rest_framework import serializers
from .models import Notification
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:model=Notification;fields=['id','category','title','body','object_type','object_id','severity','read_at','metadata','created_at'];read_only_fields=fields
