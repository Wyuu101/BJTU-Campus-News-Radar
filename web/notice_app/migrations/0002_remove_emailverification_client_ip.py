from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("notice_app", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="emailverification",
            name="client_ip",
        ),
    ]
