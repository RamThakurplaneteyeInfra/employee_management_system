from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("farm_services", "0003_farmservicerequest_puc"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmservicerequest",
            name="department",
            field=models.CharField(
                choices=[("farm", "Farm"), ("infra", "Infra")],
                db_index=True,
                default="farm",
                max_length=10,
            ),
        ),
    ]
