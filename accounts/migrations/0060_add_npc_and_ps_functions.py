from django.db import migrations


def add_npc_and_ps_functions(apps, schema_editor):
    Functions = apps.get_model("accounts", "Functions")
    for name in ("NPC", "P&S"):
        Functions.objects.get_or_create(function=name)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0059_fix_applied_at_backfill"),
    ]

    operations = [
        migrations.RunPython(add_npc_and_ps_functions, migrations.RunPython.noop),
    ]
