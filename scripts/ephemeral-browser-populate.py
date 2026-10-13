#!/usr/bin/env python3
"""Create obviously fictional GRC UX fixtures only on the disposable CI tenant.

This helper MUST never run on customer installations. It sends a small
Django ORM script to the already installed backend container, does not modify
application schemas, and intentionally creates no rights-restricted frameworks.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

FIXTURE = r"""
import os
from django.contrib.auth import get_user_model
from apps.tenancy.models import Tenant, TenantMembership
from apps.organizations.models import OrganizationUnit
from apps.assets.models import Asset
from apps.controls.models import Control, ControlImplementation
from apps.risks.models import Risk, RiskMethodology, RiskEvaluation, RiskTreatment
from apps.risks.services import evaluate_risk, methodology_defaults
from apps.actions.models import Action
from apps.evidence.models import Evidence, EvidenceLink

tenant = Tenant.objects.get(code=os.environ["GRC_VISUAL_TENANT"], status="active")
user = get_user_model().objects.get(username=os.environ["GRC_VISUAL_USER"])
assert TenantMembership.objects.filter(tenant=tenant, user=user, is_active=True, role_code="admin").exists()
assert not Risk.objects.filter(tenant=tenant).exists()
assert not Control.objects.filter(tenant=tenant).exists()
assert not Evidence.objects.filter(tenant=tenant).exists()

unit = OrganizationUnit.objects.create(
    tenant=tenant, code="CI-UNIT", name="واحد فرضی فناوری اطلاعات",
    unit_type="company", status="active",
)
asset = Asset.objects.create(
    tenant=tenant, organization_unit=unit, asset_type="application",
    code="CI-ASSET-01", title="سامانه آزمایشی ثبت سفارش",
    owner=user, criticality=3, status="active",
)
control = Control.objects.create(
    tenant=tenant, code="ci-access-review",
    title="کنترل نمونه بازبینی دسترسی",
    description="صرفاً داده مصنوعی آزمون مرورگر؛ نه کنترل استاندارد مصوب",
    control_type="technical", nature="preventive",
    status="draft", created_by=user,
)
ControlImplementation.objects.create(
    tenant=tenant, control=control, organization_unit=unit, owner=user,
    implementation_status="planned", effectiveness="not_assessed",
    implementation_description="برنامه فرضی بدون شواهد اجرای عملیاتی",
)
risk = Risk.objects.create(
    tenant=tenant, organization_unit=unit, asset=asset,
    code="CI-RISK-001", title="ریسک آزمایشی دسترسی نامجاز",
    scenario="سناریوی کاملاً فرضی برای آزمون گردش کار رابط کاربری",
    cause="خطای ساختگی در سطح دسترسی",
    consequence="توقف فرضی خدمت آزمایشی",
    owner=user, status="open",
)
cfg = methodology_defaults()
method = RiskMethodology.objects.create(
    tenant=tenant, name="روش ۵ در ۵ آزمایشی",
    likelihood_scale=cfg["likelihood_scale"],
    impact_scale=cfg["impact_scale"],
    thresholds=cfg["thresholds"], formula="product", status="active",
    is_default=True,
)
evaluation = evaluate_risk(
    risk=risk, methodology=method,
    evaluation_type=RiskEvaluation.EvaluationType.RESIDUAL,
    likelihood=2, impact=3, user=user,
)
treatment = RiskTreatment.objects.create(
    risk=risk, strategy="reduce",
    description="برنامه فرضی کاهش ریسک، هنوز تصویب نشده است",
    owner=user, status="planned", approval_status="not_submitted",
)
Action.objects.create(
    tenant=tenant, organization_unit=unit,
    title="اقدام آزمایشی بازبینی مجوزهای کاربران",
    owner=user, priority="medium", status="todo", progress=0,
    source_type="risk_treatment", source_id=treatment.id,
)
evidence = Evidence.objects.create(
    tenant=tenant, organization_unit=unit,
    title="شاهد نمونه صورتجلسه بررسی دسترسی",
    description="متن فرضی و فاقد هرگونه اطلاعات مشتری",
    evidence_type="text", text_content="صرفاً شواهد مصنوعی برای UI",
    source="synthetic-ci-only", owner=user, classification="internal",
)
EvidenceLink.objects.create(
    tenant=tenant, evidence=evidence, object_type="risk",
    object_id=risk.id, relation_type="supports",
)
assert not Control.objects.get(pk=control.pk).status == "implemented"
assert RiskTreatment.objects.get(pk=treatment.pk).approval_status == "not_submitted"
assert ControlImplementation.objects.get(control=control).effectiveness == "not_assessed"
print("CI_SYNTHETIC_POPULATED_READY")
"""


def main() -> int:
    if not (os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("GRC_BROWSER_VISUAL_EPHEMERAL_ONLY") == "YES"
            and os.environ.get("GRC_BROWSER_POPULATED_EPHEMERAL_ONLY") == "YES"):
        raise SystemExit("Synthetic fixtures require all three explicit ephemeral CI guards.")
    if len(sys.argv) != 2:
        raise SystemExit("usage: ephemeral-browser-populate.py <installed-repository>")
    install = Path(sys.argv[1]).resolve(strict=True)
    if not (install / "docker-compose.pilot.yml").is_file():
        raise SystemExit("Missing genuine installed Compose source.")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if not run_id.isdecimal():
        raise SystemExit("Missing disposable GitHub run identifier.")
    command = [
        "docker", "compose", "--env-file", ".env",
        "-f", "docker-compose.pilot.yml",
        "-f", "docker-compose.pilot.tls.yml",
        "exec", "-T",
        "-e", "GRC_VISUAL_USER=ci-installed-admin",
        "-e", "GRC_VISUAL_TENANT=ci-installed-" + run_id,
        "backend", "python", "manage.py", "shell", "-c", FIXTURE,
    ]
    result = subprocess.run(
        command, cwd=install, capture_output=True, text=True,
        timeout=65, check=False,
    )
    # Logs are deliberately not forwarded: no configuration or auth material.
    if result.returncode != 0 or "CI_SYNTHETIC_POPULATED_READY" not in result.stdout:
        raise SystemExit("Synthetic fixture preparation FAILED; see controlled runner access.")
    print("Disposable only: fictional unit, asset, risk, evaluation, control,")
    print("planned implementation, unapproved treatment, action and text evidence seeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
