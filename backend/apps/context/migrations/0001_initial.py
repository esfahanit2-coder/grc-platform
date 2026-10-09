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
        ("controls", "0003_sync_model_state"),
        ("internal_audits", "0002_sync_model_state"),
    ]
    operations = [
      migrations.CreateModel(name="BusinessProcess", fields=[("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("deleted_at", models.DateTimeField(null=True, blank=True)),
("code", models.CharField(max_length=100)), ("name", models.CharField(max_length=255)),
("description", models.TextField(blank=True)),
("criticality", models.PositiveSmallIntegerField(default=3, choices=[(1, "Very low"), (2, "Low"), (3, "Moderate"), (4, "High"), (5, "Critical")])),
("status", models.CharField(max_length=20, default="draft", choices=[("draft","Draft"),("active","Active"),("inactive","Inactive"),("archived","Archived")])),
("metadata", models.JSONField(default=dict, blank=True)),
("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="business_processes", to="tenancy.tenant")),
("organization_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="business_processes", to="organizations.organizationunit")),
("parent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="children", to="context.businessprocess")),
("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owned_business_processes", to=settings.AUTH_USER_MODEL)),]),
      migrations.CreateModel(name="RiskProcess", fields=[("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("deleted_at", models.DateTimeField(null=True, blank=True)),
("relationship_type", models.CharField(max_length=30, default="impacts")),
("rationale", models.TextField(blank=True)),
("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="risk_process_links", to="tenancy.tenant")),
("business_process", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="risk_links", to="context.businessprocess")),
("risk", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="process_links", to="risks.risk")),]),
      migrations.CreateModel(name="ControlImplementationProcess", fields=[("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("deleted_at", models.DateTimeField(null=True, blank=True)),
("relationship_type", models.CharField(max_length=30, default="applies_to")),
("rationale", models.TextField(blank=True)),
("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="control_process_links", to="tenancy.tenant")),
("business_process", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="control_links", to="context.businessprocess")),
("control_implementation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="process_links", to="controls.controlimplementation")),]),
      migrations.CreateModel(name="AuditProcess", fields=[("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("deleted_at", models.DateTimeField(null=True, blank=True)),
("relationship_type", models.CharField(max_length=30, default="in_scope")),
("rationale", models.TextField(blank=True)),
("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_process_links", to="tenancy.tenant")),
("business_process", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_links", to="context.businessprocess")),
("audit_engagement", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="process_links", to="internal_audits.auditengagement")),]),
      migrations.AddConstraint(model_name="businessprocess", constraint=models.UniqueConstraint(fields=("tenant","code"),name="uq_businessprocess_tenant_code")),
      migrations.AddConstraint(model_name="riskprocess", constraint=models.UniqueConstraint(fields=("risk","business_process","relationship_type"),condition=Q(deleted_at__isnull=True),name="uq_active_risk_process")),
      migrations.AddConstraint(model_name="controlimplementationprocess", constraint=models.UniqueConstraint(fields=("control_implementation","business_process","relationship_type"),condition=Q(deleted_at__isnull=True),name="uq_active_control_process")),
      migrations.AddConstraint(model_name="auditprocess", constraint=models.UniqueConstraint(fields=("audit_engagement","business_process","relationship_type"),condition=Q(deleted_at__isnull=True),name="uq_active_audit_process")),
    ]
