# Initial Client CRM: CurrentClientStage, ClientProfile, ClientProfileMembers, ClientConversation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_stages(apps, schema_editor):
    CurrentClientStage = apps.get_model("Clients", "CurrentClientStage")
    for name in ("Leads", "Qualified", "Demo", "Proposal", "Performer", "Invoice", "Repeat"):
        CurrentClientStage.objects.get_or_create(name=name)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("project", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL("CREATE SCHEMA IF NOT EXISTS clients;", migrations.RunSQL.noop),
        migrations.CreateModel(
            name="CurrentClientStage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_index=True, max_length=50, unique=True)),
            ],
            options={
                "db_table": 'clients"."current_client_stage',
                "ordering": ["name"],
                "verbose_name": "current client stage",
                "verbose_name_plural": "current client stages",
            },
        ),
        migrations.CreateModel(
            name="ClientProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_name", models.CharField(db_index=True, max_length=255)),
                ("client_name", models.CharField(max_length=255)),
                ("client_contact", models.CharField(blank=True, max_length=100)),
                ("representative_contact_number", models.CharField(blank=True, max_length=100)),
                ("representative_name", models.CharField(blank=True, max_length=255)),
                ("motive", models.CharField(blank=True, max_length=255)),
                ("gst_number", models.CharField(blank=True, db_index=True, max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "Product",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="client_profiles",
                        to="project.project",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_client_profiles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "status",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        default=None,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="client_profiles",
                        to="Clients.currentclientstage",
                    ),
                ),
            ],
            options={
                "db_table": 'clients"."client_profile',
                "ordering": ["-created_at"],
                "verbose_name": "client profile",
                "verbose_name_plural": "client profiles",
            },
        ),
        migrations.CreateModel(
            name="ClientProfileMembers",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "client_profile",
                    models.ForeignKey(
                        db_column="client_profile_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="member_links",
                        to="Clients.clientprofile",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_profile_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": 'clients"."client_profile_members',
                "verbose_name": "client profile member",
                "verbose_name_plural": "client profile members",
                "unique_together": {("client_profile", "user")},
            },
        ),
        migrations.CreateModel(
            name="ClientConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("note", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "client",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations",
                        to="Clients.clientprofile",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": 'clients"."client_conversation',
                "ordering": ["-created_at"],
                "verbose_name": "client conversation",
                "verbose_name_plural": "client conversations",
            },
        ),
        migrations.AddField(
            model_name="clientprofile",
            name="members",
            field=models.ManyToManyField(
                blank=True,
                related_name="client_profiles",
                through="Clients.ClientProfileMembers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(create_stages, noop),
        migrations.AddIndex(
            model_name="clientprofile",
            index=models.Index(fields=["-created_at"], name="client_profile_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="clientprofile",
            index=models.Index(fields=["company_name"], name="client_profile_company_idx"),
        ),
        migrations.AddIndex(
            model_name="clientprofilemembers",
            index=models.Index(fields=["client_profile_id"], name="client_members_profile_idx"),
        ),
        migrations.AddIndex(
            model_name="clientprofilemembers",
            index=models.Index(fields=["user_id"], name="client_members_user_idx"),
        ),
        migrations.AddIndex(
            model_name="clientconversation",
            index=models.Index(fields=["client_id", "-created_at"], name="client_conv_client_created_idx"),
        ),
    ]
