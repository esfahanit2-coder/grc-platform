from apps.common.scoped_registers import ScopedEntityViewSet, ScopedLinkViewSet
from .models import AuditProcess, BusinessProcess, ControlImplementationProcess, RiskProcess
from .serializers import AuditProcessSerializer, BusinessProcessSerializer, ControlImplementationProcessSerializer, RiskProcessSerializer

class BusinessProcessViewSet(ScopedEntityViewSet):
    model = BusinessProcess
    serializer_class = BusinessProcessSerializer
    related_link_names = ("risk_links", "control_links", "audit_links")
    read_permissions = (("process.view", "organization_unit_id"),)
    write_permissions = (("process.manage", "organization_unit_id"),)

class RiskProcessViewSet(ScopedLinkViewSet):
    model = RiskProcess
    serializer_class = RiskProcessSerializer
    endpoints = ("business_process", "risk")
    read_permissions = (("process.view", "business_process__organization_unit_id"), ("risk.view", "risk__organization_unit_id"))
    write_permissions = (("process.manage", "business_process__organization_unit_id"), ("risk.manage", "risk__organization_unit_id"))

class ControlImplementationProcessViewSet(ScopedLinkViewSet):
    model = ControlImplementationProcess
    serializer_class = ControlImplementationProcessSerializer
    endpoints = ("business_process", "control_implementation")
    read_permissions = (("process.view", "business_process__organization_unit_id"), ("control.implementation.view", "control_implementation__organization_unit_id"))
    write_permissions = (("process.manage", "business_process__organization_unit_id"), ("control.implementation.manage", "control_implementation__organization_unit_id"))

class AuditProcessViewSet(ScopedLinkViewSet):
    model = AuditProcess
    serializer_class = AuditProcessSerializer
    endpoints = ("business_process", "audit_engagement")
    read_permissions = (("process.view", "business_process__organization_unit_id"), ("internal_audit.view", "audit_engagement__organization_unit_id"))
    write_permissions = (("process.manage", "business_process__organization_unit_id"), ("internal_audit.manage", "audit_engagement__organization_unit_id"))
