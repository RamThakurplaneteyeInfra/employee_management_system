from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("CustomerPanel", "0003_customerpanelentrymembers"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerpanelentry",
            name="client_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="customerpanelentry",
            name="client_contact",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
