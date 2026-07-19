from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="DailyMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True)),
                ("new_notice_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "web_daily_metrics", "ordering": ["date"]},
        ),
        migrations.CreateModel(
            name="EmailVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email_hash", models.CharField(db_index=True, max_length=64)),
                ("encrypted_email", models.TextField()),
                ("code_hash", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField()),
                ("cooldown_until", models.DateTimeField()),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("client_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "web_email_verifications"},
        ),
        migrations.CreateModel(
            name="Subscriber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("encrypted_email", models.TextField()),
                ("preferences", models.JSONField(blank=True, default=list)),
                ("known_sections", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "web_subscribers", "ordering": ["-updated_at"]},
        ),
        migrations.AddIndex(
            model_name="emailverification",
            index=models.Index(fields=["email_hash", "-created_at"], name="web_ev_hash_created_idx"),
        ),
    ]
