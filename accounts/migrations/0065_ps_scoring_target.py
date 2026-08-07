# P&S monthly service scoring targets.

from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0064_dm_targets_and_work"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PsScoringTarget",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("year", models.PositiveSmallIntegerField()),
                ("month", models.PositiveSmallIntegerField()),
                (
                    "monthly_quantity_target",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        max_digits=14,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.001"))],
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "profile",
                    models.ForeignKey(
                        db_column="employee_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ps_scoring_targets",
                        to="accounts.profile",
                        to_field="Employee_id",
                    ),
                ),
                (
                    "set_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="set_by",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ps_targets_set",
                        to=settings.AUTH_USER_MODEL,
                        to_field="username",
                    ),
                ),
            ],
            options={
                "verbose_name": "P&S scoring target",
                "verbose_name_plural": "P&S scoring targets",
                "db_table": 'login_details"."ps_scoring_targets',
                "indexes": [
                    models.Index(fields=["profile", "year", "month"], name="ps_targets_emp_ym_idx"),
                ],
                "unique_together": {("profile", "year", "month")},
            },
        ),
    ]
