import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenancy", "0001_initial"),
        ("organizations", "0002_sync_index_names"),
        ("risks", "0002_sync_index_names"),
    ]
    operations = [
        migrations.CreateModel(
            name="Objective",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("objective_type", models.CharField(max_length=24, default="strategic", choices=[("strategic", "Strategic"), ("operational", "Operational"), ("financial", "Financial"), ("compliance", "Compliance"), ("security", "Security"), ("resilience", "Resilience")])),
                ("status", models.CharField(max_length=20, default="draft", choices=[("draft", "Draft"), ("active", "Active"), ("achieved", "Achieved"), ("retired", "Retired"), ("archived", "Archived")])),
                ("target_date", models.DateField(null=True, blank=True)),
                ("metadata", models.JSONField(default=dict, blank=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="objectives", to="tenancy.tenant")),
                ("organization_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="objectives", to="organizations.organizationunit")),
                ("parent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="children", to="objectives.objective")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owned_objectives", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="RiskObjective",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("relationship_type", models.CharField(max_length=20, default="threatens", choices=[("threatens", "Threatens"), ("supports", "Supports"), ("dependency", "Dependency")])),
                ("rationale", models.TextField(blank=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="risk_objective_links", to="tenancy.tenant")),
                ("risk", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="objective_links", to="risks.risk")),
                ("objective", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="risk_links", to="objectives.objective")),
            ],
        ),
        migrations.AddConstraint(model_name="objective", constraint=models.UniqueConstraint(fields=("tenant", "code"), name="uq_objective_tenant_code")),
        migrations.AddConstraint(model_name="riskobjective", constraint=models.UniqueConstraint(fields=("risk", "objective", "relationship_type"), condition=Q(deleted_at__isnull=True), name="uq_active_risk_objective")),
    ]
