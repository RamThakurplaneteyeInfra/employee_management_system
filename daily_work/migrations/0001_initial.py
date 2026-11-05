from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import daily_work.categories


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE SCHEMA IF NOT EXISTS daily_work;",
            migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="DailyProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("project_name", models.CharField(max_length=255)),
                ("project_description", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")],
                        default="active",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "team_lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="daily_work_led_projects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Daily work project",
                "db_table": 'daily_work"."DailyProject',
                "ordering": ["project_name", "id"],
            },
        ),
        migrations.CreateModel(
            name="ProjectAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "member_type",
                    models.CharField(
                        choices=[("employee", "Employee"), ("intern", "Intern")],
                        max_length=10,
                    ),
                ),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="daily_work.dailyproject",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="daily_work_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Project assignment",
                "db_table": 'daily_work"."ProjectAssignment',
            },
        ),
        migrations.CreateModel(
            name="DailyWorkReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report_date", models.DateField()),
                ("employee_name", models.CharField(blank=True, default="", max_length=255)),
                ("employee_category", models.CharField(blank=True, default="", max_length=255)),
                ("updates", models.JSONField(default=daily_work.categories.empty_updates)),
                (
                    "status",
                    models.CharField(
                        choices=[("submitted", "Submitted")],
                        default="submitted",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="daily_work_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reports",
                        to="daily_work.dailyproject",
                    ),
                ),
            ],
            options={
                "verbose_name": "Daily work report",
                "db_table": 'daily_work"."DailyWorkReport',
                "ordering": ["-report_date", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectassignment",
            constraint=models.UniqueConstraint(
                fields=("project", "user"),
                name="daily_work_one_assignment_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="dailyworkreport",
            constraint=models.UniqueConstraint(
                fields=("employee", "project", "report_date"),
                name="daily_work_one_report_per_day",
            ),
        ),
    ]
