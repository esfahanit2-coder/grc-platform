from rest_framework import generics
from apps.identity.services import require_whole_tenant_permission
from apps.tenancy.services import resolve_tenant_for_request
from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventListView(generics.ListAPIView):
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        tenant = resolve_tenant_for_request(self.request)
        require_whole_tenant_permission(self.request.user, tenant, "audit.view")
        qs = AuditEvent.objects.filter(tenant=tenant).select_related("actor")
        params = self.request.query_params
        if params.get("action"):
            qs = qs.filter(action=params["action"])
        if params.get("category"):
            qs = qs.filter(category=params["category"])
        if params.get("actor"):
            qs = qs.filter(actor_username__icontains=params["actor"])
        if params.get("object_type"):
            qs = qs.filter(object_type=params["object_type"])
        if params.get("outcome"):
            qs = qs.filter(outcome=params["outcome"])
        return qs.order_by("-created_at")
