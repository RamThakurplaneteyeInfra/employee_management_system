"""
Migration to remove Event and Meeting models from the Django state.

NOTE: This migration declares DeleteModel operations for Event and Meeting.
If the underlying tables already exist and you do NOT want Django to drop them,
apply this migration with --fake / --fake-initial so only the migration state is updated.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0014_reminder"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Event",
        ),
        migrations.DeleteModel(
            name="Meeting",
        ),
    ]

