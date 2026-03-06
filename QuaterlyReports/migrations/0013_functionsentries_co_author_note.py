# Add co_author_note to FunctionsEntries (co_author can share details to creator before/after approval).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("QuaterlyReports", "0012_rename_note_to_original_entry_and_shared_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="functionsentries",
            name="co_author_note",
            field=models.TextField(blank=True, default=""),
        ),
    ]
