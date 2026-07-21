"""
Quarterly casual-leave credit for every active employee.

Run on the 1st of January, April, July and October (Windows Task Scheduler /
cron / Celery Beat). Each successful run does the following, and ONLY the
following:

* Adds Decimal("2") to `LeaveSummary.casual_leaves` for every employee whose
  `Profile.Date_of_join` is on or before today, whose role is not Intern, and
  whose `last_casual_credit_on` is NOT in the current calendar quarter.

  Casual leave ACCUMULATES - unused balance from previous quarters carries
  forward and the new quarterly credit is added on top.

* Stamps `last_casual_credit_on = today` on the same rows so re-runs inside
  the same quarter are no-ops (idempotent).

No other field on `LeaveSummary` is read or written. No other model is
touched. The leave-application flow (leave_views.py / signals.py) is not
invoked.

Examples
--------
Dry run (no DB writes, just prints how many rows WOULD be credited):
    python manage.py credit_casual_leave --dry-run

Real run:
    python manage.py credit_casual_leave

Schedule (Windows Task Scheduler, every 3 months on the 1st of Jan/Apr/Jul/Oct
at 00:15):
    schtasks /Create /SC MONTHLY /MO 3 /D 1 /M JAN,APR,JUL,OCT ^
      /TN "CasualLeaveQuarterly" ^
      /TR "<full-path-to-venv>\\Scripts\\python.exe <full-path-to-project>\\manage.py credit_casual_leave" ^
      /ST 00:15
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import LeaveSummary, Profile


def _quarter_start(today):
    """Return the first day of the quarter that `today` falls into."""
    quarter_first_month = ((today.month - 1) // 3) * 3 + 1
    return today.replace(month=quarter_first_month, day=1)


class Command(BaseCommand):
    help = (
        "Credits +2 casual leaves to every eligible employee. Idempotent "
        "within the same calendar quarter. Run quarterly (Jan/Apr/Jul/Oct 1st). "
        "Use --dry-run to preview."
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
        q_start = _quarter_start(today)

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

        # Skip rows already credited in the current quarter (last_casual_credit_on >= q_start).
        affected_qs = (
            LeaveSummary.objects.filter(user__username__in=eligible_usernames)
            .exclude(last_casual_credit_on__gte=q_start)
        )
        affected_count = affected_qs.count()

        if affected_count == 0:
            self.stdout.write(self.style.NOTICE(
                f"All eligible employees already credited for quarter starting {q_start:%Y-%m-%d}; nothing to do."
            ))
            return

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f"[dry-run] Would credit +2 casual leaves to {affected_count} employee(s) "
                f"for quarter starting {q_start:%Y-%m-%d}."
            ))
            return

        # Atomic, single UPDATE. F() adds on top of the existing balance so
        # unused casual leave carries forward.
        with transaction.atomic():
            updated = affected_qs.update(
                casual_leaves=F("casual_leaves") + Decimal("2"),
                last_casual_credit_on=today,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Credited +2 casual leaves to {updated} employee(s) for quarter starting {q_start:%Y-%m-%d}."
        ))
