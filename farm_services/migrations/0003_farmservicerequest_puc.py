from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("farm_services", "0002_farmservicesubtask"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmservicerequest",
            name="puc",
            field=models.BooleanField(default=False),
        ),
    ]
