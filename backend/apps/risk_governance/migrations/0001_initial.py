import uuid
import django.core.validators
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
        migrations.CreateModel(name="RiskAppetiteStatement", fields=[
("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("deleted_at", models.DateTimeField(null=True, blank=True)),
("code", models.CharField(max_length=100)),
("version", models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
("title", models.CharField(max_length=255)),
("description", models.TextField(blank=True)),
("status", models.CharField(max_length=16, default="draft", choices=[("draft","Draft"),("approved","Approved"),("retired","Retired")])),
("effective_from", models.DateField()),
("effective_until", models.DateField(null=True, blank=True)),
("approved_at", models.DateTimeField(null=True, blank=True)),
("metadata", models.JSONField(default=dict, blank=True)),
("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="risk_appetites", to="tenancy.tenant")),
("organization_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="risk_appetites", to="organizations.organizationunit")),
("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owned_risk_appetites", to=settings.AUTH_USER_MODEL)),
("approved_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="approved_risk_appetites", to=settings.AUTH_USER_MODEL)),]),
        migrations.CreateModel(name="RiskTolerance", fields=[
("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("deleted_at", models.DateTimeField(null=True, blank=True)),
("evaluation_type", models.CharField(max_length=16, default="residual", choices=[("current","Current"),("residual","Residual")])),
("maximum_score", models.DecimalField(max_digits=14, decimal_places=4, validators=[django.core.validators.MinValueValidator(0)])),
("description", models.TextField(blank=True)),
("statement", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tolerances", to="risk_governance.riskappetitestatement")),]),
        migrations.CreateModel(name="RiskAcceptance", fields=[
("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("deleted_at", models.DateTimeField(null=True, blank=True)),
("status", models.CharField(max_length=16, choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("superseded","Superseded")], default="pending")),
("rationale", models.TextField()),
("decision_note", models.TextField(blank=True)),
("review_on", models.DateField()),
("expires_on", models.DateField()),
("decided_at", models.DateTimeField(null=True, blank=True)),
("evaluation_type_snapshot", models.CharField(max_length=16)),
("score_snapshot", models.DecimalField(max_digits=14, decimal_places=4)),
("likelihood_snapshot", models.DecimalField(max_digits=10, decimal_places=2)),
("impact_snapshot", models.DecimalField(max_digits=10, decimal_places=2)),
("evaluated_at_snapshot", models.DateTimeField()),
("tolerance_max_snapshot", models.DecimalField(max_digits=14, decimal_places=4)),
("exceeds_tolerance", models.BooleanField(default=False)),
("exception_justification", models.TextField(blank=True)),
("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="risk_acceptances", to="tenancy.tenant")),
("risk", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acceptances", to="risks.risk")),
("evaluation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acceptances", to="risks.riskevaluation")),
("appetite", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="acceptances", to="risk_governance.riskappetitestatement")),
("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="risk_acceptance_requests", to=settings.AUTH_USER_MODEL)),
("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="risk_acceptance_decisions", to=settings.AUTH_USER_MODEL)),
("supersedes", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name="successors", to="risk_governance.riskacceptance")),]),
        migrations.AddConstraint(model_name="riskappetitestatement",
            constraint=models.UniqueConstraint(fields=("tenant","code","version"), name="uq_appetite_tenant_code_version")),
        migrations.AddConstraint(model_name="risktolerance",
            constraint=models.UniqueConstraint(fields=("statement","evaluation_type"), condition=Q(deleted_at__isnull=True), name="uq_tolerance_statement_eval")),
        migrations.AddIndex(model_name="riskacceptance", index=models.Index(fields=["tenant","risk","status"], name="accept_tenant_risk_status_idx")),
        migrations.AddIndex(model_name="riskacceptance", index=models.Index(fields=["status","review_on"], name="accept_status_review_idx")),
        migrations.AddIndex(model_name="riskacceptance", index=models.Index(fields=["status","expires_on"], name="accept_status_expiry_idx")),
    ]
