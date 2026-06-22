from decimal import Decimal

import django.core.validators
from django.conf import settings
from django.db import migrations, models


def backfill_year_month(apps, schema_editor):
    MmrRgScoringTarget = apps.get_model("accounts", "MmrRgScoringTarget")
    for row in MmrRgScoringTarget.objects.all().iterator():
        updated = getattr(row, "updated_at", None)
        if updated is not None:
            row.year = updated.year
            row.month = updated.month
        else:
            row.year = 2026
            row.month = 1
        row.save(update_fields=["year", "month"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0061_mmr_rg_scoring_target"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="mmrrgscoringtarget",
            name="year",
            field=models.PositiveSmallIntegerField(default=2026),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="mmrrgscoringtarget",
            name="month",
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_year_month, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE login_details.mmr_rg_scoring_targets
                        ADD COLUMN IF NOT EXISTS id SERIAL;
                        ALTER TABLE login_details.mmr_rg_scoring_targets
                        DROP CONSTRAINT IF EXISTS mmr_rg_scoring_targets_pkey;
                        ALTER TABLE login_details.mmr_rg_scoring_targets
                        ADD PRIMARY KEY (id);
                        ALTER TABLE login_details.mmr_rg_scoring_targets
                        ADD CONSTRAINT mmr_rg_scoring_targets_profile_year_month_uniq
                        UNIQUE (employee_id, year, month);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="mmrrgscoringtarget",
                    name="id",
                    field=models.AutoField(primary_key=True, serialize=False),
                ),
                migrations.AlterField(
                    model_name="mmrrgscoringtarget",
                    name="profile",
                    field=models.ForeignKey(
                        db_column="employee_id",
                        on_delete=models.deletion.CASCADE,
                        related_name="mmr_rg_scoring_targets",
                        to="accounts.profile",
                        to_field="Employee_id",
                    ),
                ),
                migrations.AlterUniqueTogether(
                    name="mmrrgscoringtarget",
                    unique_together={("profile", "year", "month")},
                ),
                migrations.AddIndex(
                    model_name="mmrrgscoringtarget",
                    index=models.Index(
                        fields=["profile", "year", "month"],
                        name="accounts_mm_profile_7a0f0d_idx",
                    ),
                ),
            ],
        ),
    ]
