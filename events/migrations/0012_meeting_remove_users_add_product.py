# Meeting: remove users M2M, add FK to project.Product
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0002_add_product_model"),
        ("events", "0011_rename_bookslot_date_created_idx_slots_date_b218d2_idx"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="meeting",
            name="users",
        ),
        migrations.AddField(
            model_name="meeting",
            name="product",
            field=models.ForeignKey(
                blank=True,
                db_column="product_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="meetings",
                to="project.product",
            ),
        ),
    ]
