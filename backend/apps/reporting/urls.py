from django.urls import path

from .views import FormalReportExportView, FormalReportPreviewView, ManagementDashboardView, ReportCatalogView, TemplateRenderView
from .work_center import WorkCenterView
from .soa_views import (
    SoARegisterListCreateView, SoARegisterDetailView,
    SoADecisionCreateView, SoADecisionDetailView,
)

urlpatterns = [
    path("soa/registers/", SoARegisterListCreateView.as_view(), name="soa-register-list"),
    path("soa/registers/<uuid:pk>/", SoARegisterDetailView.as_view(), name="soa-register-detail"),
    path("soa/registers/<uuid:pk>/decisions/", SoADecisionCreateView.as_view(), name="soa-decision-create"),
    path("soa/registers/<uuid:pk>/decisions/<uuid:decision_id>/", SoADecisionDetailView.as_view(), name="soa-decision-detail"),
    path("dashboard/management/", ManagementDashboardView.as_view(), name="management-dashboard"),
    path("work-center/", WorkCenterView.as_view(), name="work-center"),
    path("reports/render-template/", TemplateRenderView.as_view(), name="report-template-render"),
    path("reports/catalog/", ReportCatalogView.as_view(), name="report-catalog"),
    path("reports/preview/", FormalReportPreviewView.as_view(), name="report-preview"),
    path("reports/export/", FormalReportExportView.as_view(), name="report-export"),
]
