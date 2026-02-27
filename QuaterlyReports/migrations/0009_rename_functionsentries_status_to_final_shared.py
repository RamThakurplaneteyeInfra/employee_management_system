# Rename FunctionsEntries.status → final_Status, final_Status → shared_Status (state only; db_column unchanged)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("QuaterlyReports", "0008_alter_monthly_department_head_and_subhead_meeting_head_and_more"),
    ]

    operations = [
        # State-only renames so DB columns stay "status" and "final_status"
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name="functionsentries",
                    old_name="status",
                    new_name="final_Status_temp",
                ),
                migrations.RenameField(
                    model_name="functionsentries",
                    old_name="final_Status",
                    new_name="shared_Status",
                ),
                migrations.RenameField(
                    model_name="functionsentries",
                    old_name="final_Status_temp",
                    new_name="final_Status",
                ),
            ],
            database_operations=[],
        ),
    ]
