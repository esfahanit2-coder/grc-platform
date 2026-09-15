from django.urls import path
from .views import ManagementDashboardView,TemplateRenderView
urlpatterns=[path("dashboard/management/",ManagementDashboardView.as_view(),name="management-dashboard"),path("reports/render-template/",TemplateRenderView.as_view(),name="report-template-render")]
