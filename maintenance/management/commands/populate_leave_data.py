"""
Populate leave_types with "Full_day" and "Half_day", and create a leave_summary
for each user in auth_user with total_leaves=0 and used_leaves=0.
Run: python manage.py populate_leave_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.models import LeaveTypes, LeaveSummary


class Command(BaseCommand):
    help = "Populate leave_types (Full_day, Half_day) and create leave_summary for each auth user (values 0)."

    def handle(self, *args, **options):
        User = get_user_model()

        for name in ("Full_day", "Half_day"):
            _, created = LeaveTypes.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created leave_type: {name}"))
            else:
                self.stdout.write(f"  leave_type already exists: {name}")

        created_count = 0
        for user in User.objects.all():
            _, created = LeaveSummary.objects.get_or_create(
                user=user,
                defaults={"total_leaves": 0, "used_leaves": 0},
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Leave types and summaries done. Created {created_count} new leave_summary rows "
                f"(total users: {User.objects.count()})."
            )
        )
