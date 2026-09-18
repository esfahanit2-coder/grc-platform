from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.services import require_whole_tenant_permission
from apps.tenancy.services import resolve_tenant_for_request

from .operations import build_operational_status


class OperationsStatusView(APIView):
    def get(self, request):
        tenant = resolve_tenant_for_request(request)
        require_whole_tenant_permission(request.user, tenant, "security.view")
        return Response(build_operational_status())
