from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project", "0002_add_product_model"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="deadline",
            field=models.DateField(null=True, blank=True),
        ),
    ]

