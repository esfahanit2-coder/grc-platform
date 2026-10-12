import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenancy", "0001_initial"),
        ("organizations", "0002_sync_index_names"),
        ("frameworks", "0002_sync_index_names"),
        ("controls", "0003_sync_model_state"),
        ("risks", "0002_sync_index_names"),
    ]

    operations = [
        migrations.CreateModel(
            name="SoARegister",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(max_length=255)),
                ("revision", models.PositiveIntegerField(default=1)),
                ("status", models.CharField(choices=[("draft", "Draft / not approved")], default="draft", max_length=24)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="soa_registers", to="tenancy.tenant")),
                ("organization_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="soa_registers", to="organizations.organizationunit")),
                ("framework_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="soa_registers", to="frameworks.frameworkversion")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_soa_registers", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SoAControlDecision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("reference_kind", models.CharField(choices=[("annex_a", "Annex A reference"), ("additional", "Additional organizational control")], max_length=20)),
                ("source_identifier", models.CharField(max_length=120)),
                ("decision", models.CharField(choices=[("undecided", "Undecided"), ("included", "Included / necessary"), ("excluded", "Excluded / not selected")], default="undecided", max_length=16)),
                ("rationale", models.TextField(blank=True)),
                ("register", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="control_decisions", to="reporting.soaregister")),
                ("control", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="soa_decisions", to="controls.control")),
                ("control_implementation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="soa_decisions", to="controls.controlimplementation")),
                ("risk_treatment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="soa_decisions", to="risks.risktreatment")),
                ("last_edited_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="edited_soa_decisions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="soaregister",
            constraint=models.UniqueConstraint(
                fields=("tenant", "organization_unit", "framework_version", "revision"),
                name="uq_soa_scope_version_revision",
            ),
        ),
        migrations.AddIndex(
            model_name="soaregister",
            index=models.Index(fields=["tenant", "organization_unit", "status"], name="soa_register_scope_idx"),
        ),
        migrations.AddConstraint(
            model_name="soacontroldecision",
            constraint=models.UniqueConstraint(fields=("register", "control"), name="uq_soa_register_control"),
        ),
        migrations.AddConstraint(
            model_name="soacontroldecision",
            constraint=models.UniqueConstraint(fields=("register", "reference_kind", "source_identifier"), name="uq_soa_register_reference"),
        ),
        migrations.AddIndex(
            model_name="soacontroldecision",
            index=models.Index(fields=["register", "decision"], name="soa_decisions_state_idx"),
        ),
    ]
