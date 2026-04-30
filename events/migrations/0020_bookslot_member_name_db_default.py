# Backfill NULL member_name and set DB default (Postgres). No row deletes.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0019_bookslot_member_name"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'UPDATE "events"."Slots" SET member_name = \'[]\'::jsonb '
                "WHERE member_name IS NULL;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "events"."Slots" ALTER COLUMN member_name '
                "SET DEFAULT '[]'::jsonb;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
