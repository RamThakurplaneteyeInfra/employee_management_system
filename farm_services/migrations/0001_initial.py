from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FarmServiceRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("service_name", models.CharField(max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="farm_service_requests_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="FarmServiceTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_name", models.CharField(max_length=200)),
                ("status", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="farm_services.farmservicerequest",
                    ),
                ),
                (
                    "team_members",
                    models.ManyToManyField(
                        blank=True,
                        related_name="farm_service_tasks_assigned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.AddIndex(
            model_name="farmservicerequest",
            index=models.Index(fields=["created_by"], name="farm_servic_created_a1eb41_idx"),
        ),
        migrations.AddIndex(
            model_name="farmservicerequest",
            index=models.Index(fields=["-created_at"], name="farm_servic_created_17ad9d_idx"),
        ),
        migrations.AddIndex(
            model_name="farmservicetask",
            index=models.Index(fields=["request"], name="farm_servic_request_31c966_idx"),
        ),
        migrations.AddIndex(
            model_name="farmservicetask",
            index=models.Index(fields=["status"], name="farm_servic_status_1a736f_idx"),
        ),
    ]

