from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.actions.models import Action
from apps.assessments.models import AssessmentItem
from apps.assessments.services import create_assessment,recalculate_assessment
from apps.assets.models import Asset
from apps.controls.models import Control,ControlCategory,ControlImplementation,ControlRequirement
from apps.evidence.models import Evidence,EvidenceLink
from apps.frameworks.models import Framework,FrameworkVersion,Requirement
from apps.findings.models import Finding
from apps.organizations.models import OrganizationUnit
from apps.risks.exporters import rtp_payload
from apps.risks.models import Risk,RiskCategory,RiskControl,RiskEvaluation,RiskMethodology,RiskTreatment
from apps.risks.services import evaluate_risk,methodology_defaults
from apps.tenancy.models import Tenant,TenantMembership

class GoldenPilotScenarioTests(TestCase):
    def test_end_to_end_pilot_scenario(self):
        User=get_user_model();user=User.objects.create_user(username="pilot-owner",password="Password12345!")
        tenant=Tenant.objects.create(name="Pilot Organization",code="pilot-org");TenantMembership.objects.create(tenant=tenant,user=user,role_code="admin")
        unit=OrganizationUnit.objects.create(tenant=tenant,unit_type="company",code="HQ",name="Head Office",manager=user)
        framework=Framework.objects.create(tenant=tenant,code="pilot-baseline",name="Pilot Baseline",publisher="GRC Platform",content_source="internal",license_type="internal",status="active",created_by=user)
        version=FrameworkVersion.objects.create(framework=framework,version_code="2026.1",title="Pilot",status="active",is_locked=True,created_by=user)
        req=Requirement.objects.create(framework_version=version,code="IAM.1",title="Privileged access uses MFA",body="Original pilot content",weight=1)
        category=ControlCategory.objects.create(tenant=tenant,code="iam",name="Identity")
        control=Control.objects.create(tenant=tenant,code="CTRL-IAM-MFA",title="Privileged MFA",category=category,control_type="technical",nature="preventive",status="active",created_by=user)
        ControlRequirement.objects.create(tenant=tenant,control=control,requirement=req,coverage=100,mapping_type="strong",approved=True)
        impl=ControlImplementation.objects.create(tenant=tenant,control=control,organization_unit=unit,owner=user,implementation_status="implemented",effectiveness="effective",implementation_description="MFA enforced for privileged identities")
        asset=Asset.objects.create(tenant=tenant,organization_unit=unit,asset_type="application",code="AD-01",title="Directory Service",owner=user,criticality=5)
        risk_cat=RiskCategory.objects.create(tenant=tenant,code="cyber",name="Cyber")
        risk=Risk.objects.create(tenant=tenant,organization_unit=unit,asset=asset,category=risk_cat,code="RISK-001",title="Privileged account compromise",scenario="A privileged account is compromised.",owner=user,status="treatment")
        cfg=methodology_defaults();method=RiskMethodology.objects.create(tenant=tenant,name="Pilot 5x5",likelihood_scale=cfg["likelihood_scale"],impact_scale=cfg["impact_scale"],thresholds=cfg["thresholds"],formula="product",is_default=True)
        inherent=evaluate_risk(risk=risk,methodology=method,evaluation_type=RiskEvaluation.EvaluationType.INHERENT,likelihood=5,impact=5,user=user)
        residual=evaluate_risk(risk=risk,methodology=method,evaluation_type=RiskEvaluation.EvaluationType.RESIDUAL,likelihood=2,impact=4,user=user)
        RiskControl.objects.create(risk=risk,control_implementation=impl,relationship_type="existing")
        treatment=RiskTreatment.objects.create(risk=risk,strategy="reduce",description="Maintain MFA and monitor privileged access.",owner=user,status="in_progress")
        Action.objects.create(tenant=tenant,organization_unit=unit,title="Quarterly privileged MFA review",owner=user,priority="high",status="in_progress",progress=50,source_type="risk_treatment",source_id=treatment.id)
        assessment=create_assessment(tenant=tenant,framework_version=version,title="Pilot assurance assessment",assessment_type="compliance",owner=user,organization_unit=unit)
        item=assessment.items.get(requirement=req);item.status=AssessmentItem.Status.COMPLIANT;item.applicability=AssessmentItem.Applicability.APPLICABLE;item.assessor_comment="MFA implementation verified.";item.save();recalculate_assessment(assessment)
        evidence=Evidence.objects.create(tenant=tenant,organization_unit=unit,title="Privileged MFA configuration snapshot",evidence_type="configuration",source="pilot",owner=user,classification="internal",text_content="MFA enforcement enabled")
        EvidenceLink.objects.create(tenant=tenant,evidence=evidence,object_type="assessment_item",object_id=item.id,relation_type="proves")
        finding=Finding.objects.create(tenant=tenant,organization_unit=unit,assessment_item=item,requirement=req,control_implementation=impl,risk=risk,finding_type="observation",title="Extend review automation",description="Pilot observation for remediation workflow",severity="low",owner=user)
        Action.objects.create(tenant=tenant,organization_unit=unit,title="Automate MFA review evidence",owner=user,priority="medium",status="todo",source_type="finding",source_id=finding.id)
        self.assertEqual(inherent.level,"critical");self.assertEqual(residual.level,"medium");self.assertEqual(assessment.overall_score,Decimal("100.000"));self.assertTrue(EvidenceLink.objects.filter(object_id=item.id).exists());self.assertEqual(len(rtp_payload(risk)["treatments"]),1)
