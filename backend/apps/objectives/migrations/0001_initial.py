from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


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
                ("objective_type", models.CharField(
                    choices=[
                        ("strategic", "Strategic"),
                        ("operational", "Operational"),
                        ("financial", "Financial"),
                        ("compliance", "Compliance"),
                        ("security", "Security"),
                        ("resilience", "Resilience"),
                    ],
                    default="operational",
                    max_length=20,
                )),
                ("status", models.CharField(
                    choices=[
                        ("draft", "Draft"),
                        ("active", "Active"),
                        ("achieved", "Achieved"),
                        ("retired", "Retired"),
                    ],
                    default="draft",
                    max_length=20,
                )),
                ("target_date", models.DateField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("organization_unit", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="objectives", to="organizations.organizationunit",
                )),
                ("owner", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="owned_objectives", to=settings.AUTH_USER_MODEL,
                )),
                ("parent", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="children", to="objectives.objective",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="objectives", to="tenancy.tenant",
                )),
            ],
        ),
        migrations.CreateModel(
            name="RiskObjective",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("relationship_type", models.CharField(
                    choices=[
                        ("threatens", "Threatens"),
                        ("supports", "Supports"),
                        ("dependency", "Dependency"),
                    ],
                    default="threatens",
                    max_length=20,
                )),
                ("rationale", models.TextField(blank=True)),
                ("objective", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="risk_links", to="objectives.objective",
                )),
                ("risk", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="objective_links", to="risks.risk",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="risk_objective_links", to="tenancy.tenant",
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name="objective",
            constraint=models.UniqueConstraint(
                fields=("tenant", "code"), name="uq_objective_tenant_code"
            ),
        ),
        migrations.AddConstraint(
            model_name="riskobjective",
            constraint=models.UniqueConstraint(
                fields=("tenant", "risk", "objective", "relationship_type"),
                name="uq_risk_objective_relationship",
            ),
        ),
        migrations.AddIndex(
            model_name="objective",
            index=models.Index(fields=["tenant", "status"], name="objective_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="objective",
            index=models.Index(
                fields=["tenant", "organization_unit", "status"],
                name="objective_tenant_org_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="objective",
            index=models.Index(fields=["tenant", "owner"], name="objective_tenant_owner_idx"),
        ),
        migrations.AddIndex(
            model_name="riskobjective",
            index=models.Index(fields=["tenant", "risk"], name="objective_link_risk_idx"),
        ),
        migrations.AddIndex(
            model_name="riskobjective",
            index=models.Index(fields=["tenant", "objective"], name="objective_link_obj_idx"),
        ),
    ]
