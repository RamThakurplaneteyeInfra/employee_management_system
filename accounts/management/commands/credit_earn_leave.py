"""
Monthly earn-leave credit for every active employee.

Run on the 1st of every month (Windows Task Scheduler / cron / Celery Beat).
Each successful run does the following, and ONLY the following:

* Adds Decimal("1") to `LeaveSummary.earn_leaves` for every employee whose
  `Profile.Date_of_join` is on or before today, whose role is not Intern, and
  whose `last_earn_credit_on` is NOT in the current calendar month.
* Stamps `last_earn_credit_on = today` on the same rows so re-runs in the
  same month are no-ops (idempotent).

Earn leave ACCUMULATES - it is never reset. If an employee does not consume
their monthly credit, the balance keeps growing.

No other field on `LeaveSummary` is read or written. No other model is
touched. The leave-application flow (leave_views.py / signals.py) is not
invoked.

Examples
--------
Dry run (no DB writes, just prints how many rows WOULD be credited):
    python manage.py credit_earn_leave --dry-run

Real run:
    python manage.py credit_earn_leave

Schedule (Windows Task Scheduler, day 1 of every month at 00:10):
    schtasks /Create /SC MONTHLY /D 1 /TN "EarnLeaveMonthly" ^
      /TR "<full-path-to-venv>\\Scripts\\python.exe <full-path-to-project>\\manage.py credit_earn_leave" ^
      /ST 00:10
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import LeaveSummary, Profile


class Command(BaseCommand):
    help = (
        "Credits +1 earn leave to every eligible employee. Idempotent within "
        "the same calendar month. Run monthly. Use --dry-run to preview."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the number of rows that would be credited without writing to DB.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        today = timezone.localdate()

        # Eligible usernames: profile exists AND join date is on/before today.
        eligible_usernames = list(
            Profile.objects.filter(Date_of_join__lte=today)
            .exclude(Date_of_join__isnull=True)
            .exclude(Role__role_name="Intern")
            .values_list("Employee_id__username", flat=True)
        )

        if not eligible_usernames:
            self.stdout.write(self.style.WARNING(
                "No eligible employees (no profiles with Date_of_join <= today); nothing to do."
            ))
            return

        # Skip rows already credited this calendar month.
        affected_qs = (
            LeaveSummary.objects.filter(user__username__in=eligible_usernames)
            .exclude(
                last_earn_credit_on__year=today.year,
                last_earn_credit_on__month=today.month,
            )
        )
        affected_count = affected_qs.count()

        if affected_count == 0:
            self.stdout.write(self.style.NOTICE(
                f"All eligible employees already credited for {today:%Y-%m}; nothing to do."
            ))
            return

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f"[dry-run] Would credit +1 earn leave to {affected_count} employee(s) "
                f"for {today:%Y-%m}."
            ))
            return

        # Atomic, single UPDATE. F() ensures we never overwrite a concurrently
        # changed value, and we only touch the two columns named below.
        with transaction.atomic():
            updated = affected_qs.update(
                earn_leaves=F("earn_leaves") + Decimal("1"),
                last_earn_credit_on=today,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Credited +1 earn leave to {updated} employee(s) for {today:%Y-%m}."
        ))
