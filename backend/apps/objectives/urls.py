from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ObjectiveViewSet, RiskObjectiveViewSet

router = DefaultRouter()
router.register("objectives", ObjectiveViewSet, basename="objective")
router.register("risk-objectives", RiskObjectiveViewSet, basename="risk-objective")

urlpatterns = [path("", include(router.urls))]
