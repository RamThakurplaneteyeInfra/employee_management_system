from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("daily_work", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyWorkReportSeen",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seen_at", models.DateTimeField(auto_now_add=True)),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seen_by",
                        to="daily_work.dailyworkreport",
                    ),
                ),
                (
                    "viewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_work_reports_seen",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Daily work report seen",
                "db_table": 'daily_work"."DailyWorkReportSeen',
            },
        ),
        migrations.AddConstraint(
            model_name="dailyworkreportseen",
            constraint=models.UniqueConstraint(
                fields=("report", "viewer"),
                name="daily_work_one_seen_per_viewer",
            ),
        ),
    ]
