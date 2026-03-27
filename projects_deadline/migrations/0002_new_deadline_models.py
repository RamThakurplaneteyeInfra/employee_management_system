"""
Replace the old managed ProjectPhase with an unmanaged LegacyProjectPhase stub,
and create the new DeadlineProject + DeadlineProjectPhase tables.

SAFETY: The old project."ProjectPhase" table is NOT dropped — we only remove
it from Django state and re-register it as unmanaged so Django never touches it.
"""

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("projects_deadline", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # 1) Remove old indexes from state, then drop the managed ProjectPhase
        #    from state ONLY (SeparateDatabaseAndState keeps the real table).
        # ------------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveIndex(
                    model_name="projectphase",
                    name="projects_deadline_proj_arc_idx",
                ),
                migrations.RemoveIndex(
                    model_name="projectphase",
                    name="projects_deadline_phase_status_idx",
                ),
                migrations.DeleteModel(name="ProjectPhase"),
            ],
            database_operations=[],  # nothing happens on the real DB
        ),

        # ------------------------------------------------------------------
        # 2) Register the same table as an UNMANAGED stub (state only).
        # ------------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="LegacyProjectPhase",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ],
                    options={
                        "managed": False,
                        "db_table": 'project"."ProjectPhase',
                    },
                ),
            ],
            database_operations=[],
        ),

        # ------------------------------------------------------------------
        # 3) Create DeadlineProject table  (actually runs CREATE TABLE).
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="DeadlineProject",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("branch", models.CharField(blank=True, default="", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("PLANNING", "Planning"), ("ACTIVE", "Active"), ("COMPLETED", "Completed"), ("ON_HOLD", "On Hold")], default="PLANNING", max_length=20)),
                ("deadline", models.DateField(blank=True, null=True)),
                ("archived", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("manager", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="managed_deadline_projects", to=settings.AUTH_USER_MODEL)),
                ("members", models.ManyToManyField(blank=True, related_name="deadline_project_memberships", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_deadline_projects", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": 'project"."DeadlineProject',
                "ordering": ["-created_at"],
            },
        ),

        # ------------------------------------------------------------------
        # 4) Create DeadlineProjectPhase table  (actually runs CREATE TABLE).
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="DeadlineProjectPhase",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("date", models.DateField(blank=True, null=True)),
                ("phase_status", models.CharField(choices=[("PENDING", "Pending"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed")], default="PENDING", max_length=20)),
                ("checklist", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True, default="")),
                ("archived", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="phases", to="projects_deadline.deadlineproject")),
                ("team_lead", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deadline_phase_leads", to=settings.AUTH_USER_MODEL)),
                ("members", models.ManyToManyField(blank=True, related_name="deadline_phase_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": 'project"."DeadlineProjectPhase',
                "ordering": ["sort_order", "created_at"],
            },
        ),
    ]
