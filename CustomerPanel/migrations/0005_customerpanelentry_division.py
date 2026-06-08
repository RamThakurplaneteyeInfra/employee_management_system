from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("CustomerPanel", "0004_customer_entry_client_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerpanelentry",
            name="division",
            field=models.CharField(
                blank=True,
                choices=[("farm", "Farm"), ("infra", "Infra")],
                db_index=True,
                max_length=10,
                null=True,
            ),
        ),
    ]
