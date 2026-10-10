from rest_framework.routers import DefaultRouter
from .views import (
    ApplicabilityViewSet, CriterionMappingViewSet, GenericAssessmentItemViewSet,
    GenericAssessmentRunViewSet, ProfileViewSet, TemplateCriterionViewSet,
    TemplateVersionViewSet, TemplateViewSet,
)

router = DefaultRouter()
router.register("assessment-templates", TemplateViewSet, basename="assessment-template")
router.register("assessment-template-versions", TemplateVersionViewSet, basename="assessment-template-version")
router.register("assessment-criteria", TemplateCriterionViewSet, basename="assessment-criterion")
router.register("assessment-profiles", ProfileViewSet, basename="assessment-profile")
router.register("assessment-criterion-mappings", CriterionMappingViewSet, basename="assessment-criterion-mapping")
router.register("generic-assessments", GenericAssessmentRunViewSet, basename="generic-assessment")
router.register("generic-assessment-items", GenericAssessmentItemViewSet, basename="generic-assessment-item")
router.register("assessment-applicability-decisions", ApplicabilityViewSet, basename="assessment-applicability")
urlpatterns = router.urls
