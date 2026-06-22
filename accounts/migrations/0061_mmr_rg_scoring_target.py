from decimal import Decimal

import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0060_add_npc_and_ps_functions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MmrRgScoringTarget",
            fields=[
                (
                    "profile",
                    models.OneToOneField(
                        db_column="employee_id",
                        on_delete=models.deletion.CASCADE,
                        primary_key=True,
                        related_name="mmr_rg_scoring_target",
                        serialize=False,
                        to="accounts.profile",
                        to_field="Employee_id",
                    ),
                ),
                (
                    "customer_panel_target_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                    ),
                ),
                (
                    "proposal_target_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                    ),
                ),
                ("profile_count_target", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "proforma_target_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "set_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="set_by",
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="mmr_rg_targets_set",
                        to=settings.AUTH_USER_MODEL,
                        to_field="username",
                    ),
                ),
            ],
            options={
                "verbose_name": "MMR/RG scoring target",
                "verbose_name_plural": "MMR/RG scoring targets",
                "db_table": 'login_details"."mmr_rg_scoring_targets',
            },
        ),
    ]
