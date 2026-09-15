from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenancy.services import resolve_tenant_for_request
from .models import Notification
from .serializers import NotificationSerializer
from .services import mark_read
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=NotificationSerializer
    def _tenant(self):return resolve_tenant_for_request(self.request)
    def get_queryset(self):
        qs=Notification.objects.filter(tenant=self._tenant(),user=self.request.user,deleted_at__isnull=True)
        if self.request.query_params.get('unread') in {'1','true'}:qs=qs.filter(read_at__isnull=True)
        return qs.order_by('-created_at')
    @action(detail=True,methods=['post'])
    def read(self,request,pk=None):return Response(self.get_serializer(mark_read(self.get_object())).data)
    @action(detail=False,methods=['post'],url_path='read-all')
    def read_all(self,request):
        count=self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now(),updated_at=timezone.now());return Response({'updated':count})
    @action(detail=False,methods=['get'])
    def summary(self,request):return Response({'unread':self.get_queryset().filter(read_at__isnull=True).count()})
