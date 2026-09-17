from django.urls import path

from .views import ManagementDashboardView, TemplateRenderView
from .work_center import WorkCenterView

urlpatterns = [
    path("dashboard/management/", ManagementDashboardView.as_view(), name="management-dashboard"),
    path("work-center/", WorkCenterView.as_view(), name="work-center"),
    path("reports/render-template/", TemplateRenderView.as_view(), name="report-template-render"),
]
