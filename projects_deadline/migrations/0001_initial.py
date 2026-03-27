from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("project", "0002_add_product_model"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectPhase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("date", models.DateField(blank=True, null=True)),
                ("is_scheduled", models.BooleanField(default=True)),
                (
                    "phase_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("IN_PROGRESS", "In Progress"),
                            ("COMPLETED", "Completed"),
                        ],
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                ("archived", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phases",
                        to="project.project",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_project_phases",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": 'project"."ProjectPhase',
                "verbose_name": "Project Phase",
                "verbose_name_plural": "Project Phases",
                "ordering": ["date", "created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="projectphase",
            index=models.Index(fields=["project", "archived"], name="projects_deadline_proj_arc_idx"),
        ),
        migrations.AddIndex(
            model_name="projectphase",
            index=models.Index(fields=["phase_status"], name="projects_deadline_phase_status_idx"),
        ),
    ]

