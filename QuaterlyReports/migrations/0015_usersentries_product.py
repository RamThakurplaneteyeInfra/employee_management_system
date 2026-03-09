# Add product FK to UsersEntries so each entry can be attached to a product.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0002_add_product_model"),
        ("QuaterlyReports", "0014_alter_plannedactions_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersentries",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users_entries",
                to="project.product",
                db_column="product_id",
            ),
        ),
    ]
