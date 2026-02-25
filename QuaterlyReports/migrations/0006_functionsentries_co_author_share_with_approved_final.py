# Generated manually: co_author, share_with, approved_by_coauthor, final_Status on FunctionsEntries

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("task_management", "0003_taskcreateandeditlogs_taskstatus_tasktypes_and_more"),
        ("QuaterlyReports", "0005_alter_functionsentries_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="functionsentries",
            name="co_author",
            field=models.ForeignKey(
                blank=True,
                db_column="co_author",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="co_authored_entries",
                to=settings.AUTH_USER_MODEL,
                to_field="username",
            ),
        ),
        migrations.AddField(
            model_name="functionsentries",
            name="share_with",
            field=models.ForeignKey(
                blank=True,
                db_column="share_with",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="shared_entries",
                to=settings.AUTH_USER_MODEL,
                to_field="username",
            ),
        ),
        migrations.AddField(
            model_name="functionsentries",
            name="approved_by_coauthor",
            field=models.BooleanField(db_column="approved_by_coauthor", default=False),
        ),
        migrations.AddField(
            model_name="functionsentries",
            name="final_Status",
            field=models.ForeignKey(
                blank=True,
                db_column="final_status",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="functions_entries_final",
                to="task_management.taskstatus",
            ),
        ),
        migrations.AlterField(
            model_name="functionsentries",
            name="status",
            field=models.ForeignKey(
                blank=True,
                db_column="status",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="functions_entries_initial",
                to="task_management.taskstatus",
            ),
        ),
    ]
