from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0007_expense_tracker_vendor"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="assigned_to",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Name of the employee this asset is assigned to.",
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="asset",
            name="floor",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="asset",
            name="author",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
