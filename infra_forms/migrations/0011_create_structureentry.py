"""Create unified StructureEntry table.

Old per-module tables (Boq/Lidar/Sar StructureEntry) are kept untouched as a backup.
This migration only adds the new unified table; no existing data is altered.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("infra_forms", "0010_projectcatalog_service_json"),
    ]

    operations = [
        migrations.CreateModel(
            name="StructureEntry",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("project_name", models.CharField(blank=True, default="", max_length=160)),
                ("team_lead_name", models.CharField(blank=True, default="", max_length=120)),
                ("branch", models.CharField(blank=True, default="INFRA_CORE", max_length=80)),
                ("date_of_entry", models.DateField(blank=True, null=True)),
                ("route_corridor", models.CharField(blank=True, max_length=200)),
                ("sr_no", models.CharField(blank=True, max_length=40)),
                ("chainage", models.CharField(blank=True, default="", max_length=120)),
                ("structure_type", models.CharField(blank=True, default="", max_length=100)),
                ("length_of_structure", models.CharField(blank=True, max_length=120)),
                ("span_arrangement", models.CharField(blank=True, max_length=200)),
                ("equipment_notes", models.TextField(blank=True)),
                (
                    "boq_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "Not set"),
                            ("Completed", "Completed"),
                            ("Missing", "Missing"),
                            ("In progress", "In progress"),
                            ("Issue-attention", "Issue-attention"),
                        ],
                        default="",
                        max_length=20,
                    ),
                ),
                ("boq_remark", models.TextField(blank=True, default="")),
                (
                    "lidar_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "Not set"),
                            ("Completed", "Completed"),
                            ("Missing", "Missing"),
                            ("In progress", "In progress"),
                            ("Issue-attention", "Issue-attention"),
                        ],
                        default="",
                        max_length=20,
                    ),
                ),
                ("lidar_remark", models.TextField(blank=True, default="")),
                (
                    "sar_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "Not set"),
                            ("Completed", "Completed"),
                            ("Missing", "Missing"),
                            ("In progress", "In progress"),
                            ("Issue-attention", "Issue-attention"),
                        ],
                        default="",
                        max_length=20,
                    ),
                ),
                ("sar_remark", models.TextField(blank=True, default="")),
                ("has_boq", models.BooleanField(default=False)),
                ("has_lidar", models.BooleanField(default=False)),
                ("has_sar", models.BooleanField(default=False)),
                ("las_file_submitted", models.BooleanField(default=False)),
                ("reports_available_on_bms_for_las", models.BooleanField(default=False)),
                ("sar_files_submitted", models.BooleanField(default=False)),
                ("reports_available_on_bms_for_sar", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "route_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="structure_entries",
                        to="infra_forms.routecorridorgroup",
                    ),
                ),
            ],
            options={
                "verbose_name": "Structure entry (unified)",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="structureentry",
            index=models.Index(fields=["-created_at"], name="infra_se_created_idx"),
        ),
        migrations.AddIndex(
            model_name="structureentry",
            index=models.Index(fields=["date_of_entry"], name="infra_se_date_idx"),
        ),
        migrations.AddIndex(
            model_name="structureentry",
            index=models.Index(fields=["route_group"], name="infra_se_routegrp_idx"),
        ),
        migrations.AddIndex(
            model_name="structureentry",
            index=models.Index(fields=["has_boq"], name="infra_se_has_boq_idx"),
        ),
        migrations.AddIndex(
            model_name="structureentry",
            index=models.Index(fields=["has_lidar"], name="infra_se_has_lidar_idx"),
        ),
        migrations.AddIndex(
            model_name="structureentry",
            index=models.Index(fields=["has_sar"], name="infra_se_has_sar_idx"),
        ),
    ]
