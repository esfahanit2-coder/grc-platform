from rest_framework.routers import DefaultRouter
from .views import RiskAcceptanceViewSet, RiskAppetiteViewSet, RiskToleranceViewSet

router = DefaultRouter()
router.register("risk-appetites", RiskAppetiteViewSet, basename="risk-appetite")
router.register("risk-tolerances", RiskToleranceViewSet, basename="risk-tolerance")
router.register("risk-acceptances", RiskAcceptanceViewSet, basename="risk-acceptance")
urlpatterns = router.urls
