"""
Monthly short-leave quota reset.

Run on the 1st of each month (scheduler / Celery Beat). Resets each
`LeaveSummary` row so `short_leaves_remaining` equals
`settings.SHORT_LEAVE_MONTHLY_QUOTA` and stamps `short_leave_credit_month_first`
to the first day of the current calendar month — but only on rows whose stamp
does not yet match this month (idempotent reruns).

This mirrors lazy rollover used on short-leave POST and GET summary.

Examples
--------
Dry run:

    python manage.py credit_short_leave_monthly --dry-run

Apply:

    python manage.py credit_short_leave_monthly
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from accounts.models import LeaveSummary


class Command(BaseCommand):
    help = (
        "Reset monthly short-leave quota for all summaries not yet stamped "
        "for the current calendar month."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print how many rows would be reset without writing.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        ms = timezone.localdate().replace(day=1)
        quota = max(0, int(getattr(settings, "SHORT_LEAVE_MONTHLY_QUOTA", 2)))
        qs = LeaveSummary.objects.exclude(short_leave_credit_month_first=ms)
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.NOTICE("Everyone already refreshed for this month."))
            return
        if dry_run:
            self.stdout.write(self.style.NOTICE(f"[dry-run] Would refresh {count} summary row(s)."))
            return
        updated = qs.update(
            short_leaves_remaining=quota,
            short_leave_credit_month_first=ms,
        )
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} LeaveSummary row(s) for {ms:%Y-%m}."))
