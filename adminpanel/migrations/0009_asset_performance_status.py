# Replace Asset.status TaskStatus FK with Performing / Nonperforming CharField.

from django.db import migrations, models


def forwards_replace_status(apps, schema_editor):
    """Drop FK column and recreate as varchar; default existing rows to Performing."""
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        # Drop FK constraint on adminpanel."Asset".current_status if present.
        cursor.execute(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'adminpanel'
              AND tc.table_name = 'Asset'
              AND kcu.column_name = 'current_status'
            """
        )
        rows = cursor.fetchall()
        for (constraint_name,) in rows:
            cursor.execute(
                f'ALTER TABLE adminpanel."Asset" DROP CONSTRAINT IF EXISTS "{constraint_name}"'
            )
        cursor.execute(
            """
            ALTER TABLE adminpanel."Asset"
            ALTER COLUMN current_status TYPE varchar(20)
            USING 'Performing'
            """
        )
        cursor.execute(
            """
            ALTER TABLE adminpanel."Asset"
            ALTER COLUMN current_status SET DEFAULT 'Performing'
            """
        )
        cursor.execute(
            """
            UPDATE adminpanel."Asset"
            SET current_status = 'Performing'
            WHERE current_status IS NULL OR current_status = ''
            """
        )
        cursor.execute(
            """
            ALTER TABLE adminpanel."Asset"
            ALTER COLUMN current_status SET NOT NULL
            """
        )


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0008_asset_floor_assigned_to"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="asset",
                    name="status",
                ),
                migrations.AddField(
                    model_name="asset",
                    name="status",
                    field=models.CharField(
                        choices=[
                            ("Performing", "Performing"),
                            ("Nonperforming", "Nonperforming"),
                        ],
                        db_column="current_status",
                        default="Performing",
                        max_length=20,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(forwards_replace_status, backwards_noop),
            ],
        ),
    ]
