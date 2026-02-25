# Generated manually for Profile <-> Functions M2M (through table in login_details)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_function_to_through(apps, schema_editor):
    """Copy existing Profile.function_id to ProfileFunction through table."""
    Profile = apps.get_model("accounts", "Profile")
    ProfileFunction = apps.get_model("accounts", "ProfileFunction")
    # Use values to read the FK id before RemoveField; column name is "function_id" in DB.
    for row in Profile.objects.values("Employee_id", "Function_id").filter(Function_id__isnull=False):
        profile = Profile.objects.get(pk=row["Employee_id"])
        ProfileFunction.objects.get_or_create(
            profile=profile,
            function_id=row["Function_id"],
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0036_profile_birthday_counter"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfileFunction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_functions",
                        to="accounts.profile",
                        to_field="Employee_id",
                        db_column="employee_id",
                    ),
                ),
                (
                    "function",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_functions",
                        to="accounts.functions",
                        db_column="function_id",
                    ),
                ),
            ],
            options={
                "db_table": 'login_details"."profile_functions',
                "verbose_name": "Profile function",
                "verbose_name_plural": "Profile functions",
                "unique_together": {("profile", "function")},
            },
        ),
        migrations.AddField(
            model_name="profile",
            name="functions",
            field=models.ManyToManyField(
                blank=True,
                related_name="profiles",
                through="accounts.ProfileFunction",
                to="accounts.functions",
                verbose_name="functions",
            ),
        ),
        migrations.RunPython(copy_function_to_through, noop_reverse),
        migrations.RemoveField(
            model_name="profile",
            name="Function",
        ),
    ]
