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
        ("controls", "0003_sync_model_state"),
        ("internal_audits", "0002_sync_model_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="BusinessProcess",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("criticality", models.DecimalField(decimal_places=2, default=3, max_digits=6)),
                ("status", models.CharField(
                    choices=[("draft", "Draft"), ("active", "Active"), ("retired", "Retired")],
                    default="draft", max_length=20,
                )),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("organization_unit", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="business_processes", to="organizations.organizationunit",
                )),
                ("owner", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="owned_business_processes", to=settings.AUTH_USER_MODEL,
                )),
                ("parent", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="children", to="processes.businessprocess",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="business_processes", to="tenancy.tenant",
                )),
            ],
        ),
        migrations.CreateModel(
            name="RiskProcess",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("relationship_type", models.CharField(
                    choices=[("primary", "Primary"), ("supporting", "Supporting"), ("dependency", "Dependency")],
                    default="primary", max_length=20,
                )),
                ("rationale", models.TextField(blank=True)),
                ("process", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="risk_links", to="processes.businessprocess",
                )),
                ("risk", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="process_links", to="risks.risk",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="risk_process_links", to="tenancy.tenant",
                )),
            ],
        ),
        migrations.CreateModel(
            name="ControlImplementationProcess",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("relationship_type", models.CharField(
                    choices=[
                        ("operates", "Operates in process"),
                        ("supports", "Supports process"),
                        ("compensating", "Compensating"),
                    ],
                    default="operates", max_length=20,
                )),
                ("rationale", models.TextField(blank=True)),
                ("control_implementation", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="process_links", to="controls.controlimplementation",
                )),
                ("process", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="control_links", to="processes.businessprocess",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="control_process_links", to="tenancy.tenant",
                )),
            ],
        ),
        migrations.CreateModel(
            name="AuditProcess",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("relationship_type", models.CharField(
                    choices=[
                        ("scope", "In scope"),
                        ("primary", "Primary process"),
                        ("supporting", "Supporting process"),
                    ],
                    default="scope", max_length=20,
                )),
                ("rationale", models.TextField(blank=True)),
                ("audit_engagement", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="process_links", to="internal_audits.auditengagement",
                )),
                ("process", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="audit_links", to="processes.businessprocess",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="audit_process_links", to="tenancy.tenant",
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name="businessprocess",
            constraint=models.UniqueConstraint(
                fields=("tenant", "code"), name="uq_business_process_tenant_code"
            ),
        ),
        migrations.AddConstraint(
            model_name="riskprocess",
            constraint=models.UniqueConstraint(
                fields=("tenant", "risk", "process", "relationship_type"),
                name="uq_risk_process_relationship",
            ),
        ),
        migrations.AddConstraint(
            model_name="controlimplementationprocess",
            constraint=models.UniqueConstraint(
                fields=("tenant", "control_implementation", "process", "relationship_type"),
                name="uq_control_process_relationship",
            ),
        ),
        migrations.AddConstraint(
            model_name="auditprocess",
            constraint=models.UniqueConstraint(
                fields=("tenant", "audit_engagement", "process", "relationship_type"),
                name="uq_audit_process_relationship",
            ),
        ),
        migrations.AddIndex(
            model_name="businessprocess",
            index=models.Index(fields=["tenant", "parent"], name="process_tenant_parent_idx"),
        ),
        migrations.AddIndex(
            model_name="businessprocess",
            index=models.Index(
                fields=["tenant", "organization_unit", "status"],
                name="process_tenant_org_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="businessprocess",
            index=models.Index(fields=["tenant", "owner"], name="process_tenant_owner_idx"),
        ),
        migrations.AddIndex(
            model_name="riskprocess",
            index=models.Index(fields=["tenant", "risk"], name="process_link_risk_idx"),
        ),
        migrations.AddIndex(
            model_name="riskprocess",
            index=models.Index(fields=["tenant", "process"], name="process_link_proc_idx"),
        ),
        migrations.AddIndex(
            model_name="controlimplementationprocess",
            index=models.Index(
                fields=["tenant", "control_implementation"], name="process_link_control_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="controlimplementationprocess",
            index=models.Index(fields=["tenant", "process"], name="process_ctrl_proc_idx"),
        ),
        migrations.AddIndex(
            model_name="auditprocess",
            index=models.Index(
                fields=["tenant", "audit_engagement"], name="process_link_audit_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="auditprocess",
            index=models.Index(fields=["tenant", "process"], name="process_audit_proc_idx"),
        ),
    ]
