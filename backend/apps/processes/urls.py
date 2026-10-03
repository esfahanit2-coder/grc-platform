from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditProcessViewSet,
    BusinessProcessViewSet,
    ControlImplementationProcessViewSet,
    RiskProcessViewSet,
)

router = DefaultRouter()
router.register("business-processes", BusinessProcessViewSet, basename="business-process")
router.register("risk-processes", RiskProcessViewSet, basename="risk-process")
router.register(
    "control-processes",
    ControlImplementationProcessViewSet,
    basename="control-process",
)
router.register("audit-processes", AuditProcessViewSet, basename="audit-process")

urlpatterns = [path("", include(router.urls))]
