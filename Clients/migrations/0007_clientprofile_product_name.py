# Nullable CharField: free-text product label when Project FK is unset.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Clients", "0006_clientprofile_branch"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientprofile",
            name="product_name",
            field=models.CharField(
                blank=True,
                help_text="Free-text product label when Product (Project) is unset or has no matching Project.",
                max_length=255,
                null=True,
            ),
        ),
    ]
