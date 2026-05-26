from django.db import migrations


def seed_leave_notification_types(apps, schema_editor):
    NotificationType = apps.get_model("notifications", "notification_type")
    names = [
        "Leave_Submitted_Alternative",
        "Leave_Alternative_Approved",
        "Leave_TeamLead_Approved",
        "Leave_HR_Approved",
        "Leave_Final_Approved",
    ]
    for name in names:
        NotificationType.objects.get_or_create(type_name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_alter_notification_from_user_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_leave_notification_types, migrations.RunPython.noop),
    ]
