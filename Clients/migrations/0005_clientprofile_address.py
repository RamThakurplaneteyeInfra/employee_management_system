# Generated manually — additive only; no data removal.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Clients", "0004_clientprofile_product_value"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientprofile",
            name="address",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Optional client or site address.",
            ),
        ),
    ]
