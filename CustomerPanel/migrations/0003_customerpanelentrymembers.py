from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("CustomerPanel", "0002_customerpanelamountlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerPanelEntryMembers",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entry",
                    models.ForeignKey(
                        db_column="entry_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="member_links",
                        to="CustomerPanel.customerpanelentry",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_panel_entry_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "customer panel entry member",
                "verbose_name_plural": "customer panel entry members",
                "db_table": 'customer_panel"."entry_members',
                "unique_together": {("entry", "user")},
            },
        ),
        migrations.AddField(
            model_name="customerpanelentry",
            name="members",
            field=models.ManyToManyField(
                blank=True,
                related_name="shared_customer_panel_entries",
                through="CustomerPanel.CustomerPanelEntryMembers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="customerpanelentrymembers",
            index=models.Index(fields=["entry_id"], name="cust_panel_ent_mem_entry_idx"),
        ),
        migrations.AddIndex(
            model_name="customerpanelentrymembers",
            index=models.Index(fields=["user_id"], name="cust_panel_ent_mem_user_idx"),
        ),
    ]
