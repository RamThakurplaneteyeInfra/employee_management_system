from django.db import migrations


def add_proforma_stage(apps, schema_editor):
    CurrentClientStage = apps.get_model("Clients", "CurrentClientStage")
    CurrentClientStage.objects.get_or_create(name="Proforma")


class Migration(migrations.Migration):

    dependencies = [
        ("Clients", "0008_clientprofile_last_reminded_at"),
    ]

    operations = [
        migrations.RunPython(add_proforma_stage, migrations.RunPython.noop),
    ]
