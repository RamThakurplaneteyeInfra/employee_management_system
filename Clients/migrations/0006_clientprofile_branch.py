# Additive only — nullable FK; existing client_profile rows keep all data.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Branch model is created in accounts 0018.
        ("accounts", "0018_branch_alter_designation_options_alter_roles_options"),
        ("Clients", "0005_clientprofile_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientprofile",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                help_text="Office branch from team_management.Branches (dropdown branch_id).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="client_profiles",
                to="accounts.branch",
            ),
        ),
    ]
