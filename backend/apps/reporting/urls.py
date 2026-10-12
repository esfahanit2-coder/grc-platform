from django.urls import path

from .views import FormalReportExportView, FormalReportPreviewView, ManagementDashboardView, ReportCatalogView, TemplateRenderView
from .work_center import WorkCenterView
from .soa_readiness import SoADraftReadinessView
from .soa_review import SoAReviewEventsView, SoAReviewRespondView
from .soa_reference_diff import SoANumericReferenceDiffView
from .soa_views import (
    SoARegisterListCreateView, SoARegisterDetailView,
    SoADecisionCreateView, SoADecisionDetailView,
)

urlpatterns = [
    path("soa/registers/", SoARegisterListCreateView.as_view(), name="soa-register-list"),
    path("soa/registers/<uuid:pk>/", SoARegisterDetailView.as_view(), name="soa-register-detail"),
    path("soa/registers/<uuid:pk>/readiness/", SoADraftReadinessView.as_view(), name="soa-register-readiness"),
    path("soa/registers/<uuid:pk>/review-requests/", SoAReviewEventsView.as_view(), name="soa-draft-review-events"),
    path("soa/registers/<uuid:pk>/review-requests/<uuid:event_id>/respond/", SoAReviewRespondView.as_view(), name="soa-draft-review-respond"),
    path("soa/registers/<uuid:pk>/reference-diff/", SoANumericReferenceDiffView.as_view(), name="soa-register-reference-diff"),
    path("soa/registers/<uuid:pk>/decisions/", SoADecisionCreateView.as_view(), name="soa-decision-create"),
    path("soa/registers/<uuid:pk>/decisions/<uuid:decision_id>/", SoADecisionDetailView.as_view(), name="soa-decision-detail"),
    path("dashboard/management/", ManagementDashboardView.as_view(), name="management-dashboard"),
    path("work-center/", WorkCenterView.as_view(), name="work-center"),
    path("reports/render-template/", TemplateRenderView.as_view(), name="report-template-render"),
    path("reports/catalog/", ReportCatalogView.as_view(), name="report-catalog"),
    path("reports/preview/", FormalReportPreviewView.as_view(), name="report-preview"),
    path("reports/export/", FormalReportExportView.as_view(), name="report-export"),
]
