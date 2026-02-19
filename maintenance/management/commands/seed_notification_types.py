"""
Seed notification types required for WebSocket notifications.
Run: python manage.py seed_notification_types
"""
from django.core.management.base import BaseCommand
from notifications.models import notification_type

DEFAULT_TYPES = [
    "Task_Created",
    "Group_message",
    "private_message",
    "Group_Created",
    "Slot_booked",
    "Meeting_scheduled",
]


class Command(BaseCommand):
    help = "Create default notification types if they do not exist."

    def handle(self, *args, **options):
        # created = []
        # for name in DEFAULT_TYPES:
        #     _, is_new = notification_type.objects.get_or_create(type_name=name)
        #     if is_new:
        #         created.append(name)
        #         self.stdout.write(self.style.SUCCESS(f"Created notification type: {name}"))
        # if not created:
        #     self.stdout.write("All notification types already exist.")
        # else:
        #     self.stdout.write(self.style.SUCCESS(f"Created {len(created)} notification type(s)."))
