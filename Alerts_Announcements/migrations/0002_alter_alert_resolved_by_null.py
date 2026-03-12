# Allow resolved_by to be null so new alerts can be created without a resolver
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Alerts_Announcements", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alert",
            name="resolved_by",
            field=models.ForeignKey(
                blank=True,
                db_column="closed_by_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="closed_alerts",
                to=settings.AUTH_USER_MODEL,
                to_field="username",
            ),
        ),
    ]
