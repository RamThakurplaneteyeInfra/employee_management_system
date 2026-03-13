from django.db import migrations, models


def create_default_client_interaction_channels(apps, schema_editor):
    ClientInteractionChannels = apps.get_model("Clients", "ClientInteractionChannels")
    for name in ("Calls", "Trial", "Demand", "Pitch"):
        ClientInteractionChannels.objects.get_or_create(medium=name)


class Migration(migrations.Migration):

    dependencies = [
        ("Clients", "0002_alter_clientprofile_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientInteractionChannels",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("medium", models.CharField(max_length=100)),
            ],
            options={
                "db_table": 'clients"."client_interaction_channels',
                "verbose_name": "client interaction channel",
                "verbose_name_plural": "client interaction channels",
            },
        ),
        migrations.AddField(
            model_name="clientconversation",
            name="medium",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="conversations",
                to="Clients.clientinteractionchannels",
                db_column="interaction_channel_id",
            ),
        ),
        migrations.RunPython(create_default_client_interaction_channels, migrations.RunPython.noop),
    ]

