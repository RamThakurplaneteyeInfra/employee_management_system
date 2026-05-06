"""
Monthly menstrual-leave reset for female employees.

Run on the 1st of every month (Windows Task Scheduler / cron / Celery Beat).
Each run sets `LeaveSummary.menstrual_leaves` to 1 for every user whose
`Profile.gender` is "Female". Unused balance from the previous month is
intentionally discarded (no carry-over).

Examples
--------
Dry run (no DB writes, just prints how many rows WOULD be reset):
    python manage.py credit_menstrual_leave --dry-run

Real run (resets menstrual_leaves to 1 for every female employee whose
balance is not already 1):
    python manage.py credit_menstrual_leave

Schedule (Windows Task Scheduler, day 1 of every month at 00:05):
    schtasks /Create /SC MONTHLY /D 1 /TN "MenstrualLeaveMonthly" ^
      /TR "<full-path-to-venv>\\Scripts\\python.exe <full-path-to-project>\\manage.py credit_menstrual_leave" ^
      /ST 00:05
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import LeaveSummary, Profile


class Command(BaseCommand):
    help = (
        "Resets menstrual_leaves to 1 for every female employee. "
        "Run monthly (e.g. 1st of each month). Use --dry-run to preview."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the number of rows that would be reset without writing to DB.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        female_usernames = list(
            Profile.objects.filter(gender__iexact="Female")
            .values_list("Employee_id__username", flat=True)
        )

        if not female_usernames:
            self.stdout.write(self.style.WARNING("No female employees found; nothing to do."))
            return

        affected_qs = (
            LeaveSummary.objects.filter(user__username__in=female_usernames)
            .exclude(menstrual_leaves=1)
        )
        affected_count = affected_qs.count()

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"[dry-run] Would reset menstrual_leaves to 1 for {affected_count} employee(s)."
                )
            )
            return

        with transaction.atomic():
            updated = affected_qs.update(menstrual_leaves=1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset menstrual_leaves to 1 for {updated} employee(s)."
            )
        )
