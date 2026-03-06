# Rename FunctionsEntries.note -> original_entry; FunctionsEntriesShare.note -> shared_note.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("QuaterlyReports", "0011_functionsentriesshare_remove_share_from_entry"),
    ]

    operations = [
        migrations.RenameField(
            model_name="functionsentries",
            old_name="note",
            new_name="original_entry",
        ),
        migrations.RenameField(
            model_name="functionsentriesshare",
            old_name="note",
            new_name="shared_note",
        ),
    ]
