import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SoADraftReviewEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("review_round", models.PositiveIntegerField()),
                ("kind", models.CharField(choices=[
                    ("requested", "Review requested"),
                    ("changes_requested", "Changes requested"),
                    ("feedback_recorded", "Review feedback recorded (not approval)"),
                    ("superseded", "Draft changed, prior request superseded"),
                ], max_length=24)),
                ("is_response", models.BooleanField(default=False)),
                ("note", models.TextField(blank=True)),
                ("draft_digest", models.CharField(max_length=64)),
                ("register", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="review_events", to="reporting.soaregister")),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="soa_review_events", to=settings.AUTH_USER_MODEL)),
                ("assigned_reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assigned_soa_review_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["review_round", "created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="soadraftreviewevent",
            constraint=models.UniqueConstraint(
                fields=("register", "review_round"),
                condition=models.Q(is_response=False, deleted_at__isnull=True),
                name="uq_soa_review_round_request",
            ),
        ),
        migrations.AddConstraint(
            model_name="soadraftreviewevent",
            constraint=models.UniqueConstraint(
                fields=("register", "review_round"),
                condition=models.Q(is_response=True, deleted_at__isnull=True),
                name="uq_soa_review_round_response",
            ),
        ),
        migrations.AddIndex(
            model_name="soadraftreviewevent",
            index=models.Index(fields=["register", "review_round"], name="soa_review_round_idx"),
        ),
    ]
