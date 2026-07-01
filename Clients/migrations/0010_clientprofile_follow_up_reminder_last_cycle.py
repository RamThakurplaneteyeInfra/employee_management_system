# follow_up_reminder_last_cycle: sync Django state with hosted DB (column may already exist).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Clients", "0009_add_proforma_stage"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE "clients"."client_profile"
                    ADD COLUMN IF NOT EXISTS follow_up_reminder_last_cycle integer NOT NULL DEFAULT 0;
                    UPDATE "clients"."client_profile"
                    SET follow_up_reminder_last_cycle = 0
                    WHERE follow_up_reminder_last_cycle IS NULL;
                    ALTER TABLE "clients"."client_profile"
                    ALTER COLUMN follow_up_reminder_last_cycle SET DEFAULT 0;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="clientprofile",
                    name="follow_up_reminder_last_cycle",
                    field=models.PositiveIntegerField(
                        default=0,
                        help_text="Follow-up reminder cycle counter (incremented on ack); 0 until first ack.",
                    ),
                ),
            ],
        ),
    ]
