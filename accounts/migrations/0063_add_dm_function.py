from django.db import migrations


def add_dm_function(apps, schema_editor):
    Functions = apps.get_model("accounts", "Functions")
    Functions.objects.get_or_create(function="DM")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0062_mmr_rg_scoring_target_monthly"),
    ]

    operations = [
        migrations.RunPython(add_dm_function, migrations.RunPython.noop),
    ]
