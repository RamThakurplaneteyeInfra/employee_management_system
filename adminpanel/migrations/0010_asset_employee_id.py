from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0009_asset_performance_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="employee_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Employee username / ID this asset is assigned to.",
                max_length=50,
            ),
        ),
    ]
