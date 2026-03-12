"""
Refresh task counts by task type for each user in auth_user.

Recomputes AssingnedTasksCount and CreatedTasksCount from Task and TaskAssignies,
so counts match actual data (e.g. after data fixes or imports).

Run: python manage.py refresh_task_count_by_type
     python manage.py refresh_task_count_by_type --dry-run
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count

from task_management.models import (
    Task,
    TaskAssignies,
    AssingnedTasksCount,
    CreatedTasksCount,
)

# Task type names used in AssingnedTasksCount / CreatedTasksCount (must match TaskTypes and model fields)
TYPE_NAMES = ["1 Day", "SOS", "10 Day", "Monthly", "Quaterly"]


def _count_field_for_type(type_name):
    """Return the count field name for a task type (e.g. '1 Day' -> 'count_1_Day')."""
    return "count_" + type_name.replace(" ", "_")


def _build_zero_counts():
    """Return a dict of type_name -> 0 for all types."""
    return {t: 0 for t in TYPE_NAMES}


class Command(BaseCommand):
    help = (
        "Refresh AssingnedTasksCount and CreatedTasksCount for every user in auth_user "
        "from current Task and TaskAssignies data (by task type)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be updated, do not write to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        User = get_user_model()

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no changes will be saved."))

        # -------- Assigned counts (per assignee, by task type) --------
        assigned_agg = (
            TaskAssignies.objects.values("assigned_to", "task__type__type_name")
            .annotate(cnt=Count("task_id"))
            .order_by()
        )
        # Group by username -> { type_name: count }
        assigned_by_user = {}
        for row in assigned_agg:
            username = row["assigned_to"]
            type_name = row["task__type__type_name"]
            if username not in assigned_by_user:
                assigned_by_user[username] = _build_zero_counts()
            if type_name in TYPE_NAMES:
                assigned_by_user[username][type_name] = row["cnt"]

        # -------- Created counts (per creator, by task type) --------
        created_agg = (
            Task.objects.values("created_by", "type__type_name")
            .annotate(cnt=Count("task_id"))
            .order_by()
        )
        created_by_user = {}
        for row in created_agg:
            username = row["created_by"]
            type_name = row["type__type_name"]
            if username not in created_by_user:
                created_by_user[username] = _build_zero_counts()
            if type_name in TYPE_NAMES:
                created_by_user[username][type_name] = row["cnt"]

        # -------- Update or create count rows for every user --------
        users = list(User.objects.all())
        updated_assigned = 0
        updated_created = 0

        with transaction.atomic():
            for user in users:
                username = user.username
                # AssingnedTasksCount
                assigned_counts = assigned_by_user.get(username, _build_zero_counts())
                obj, created = AssingnedTasksCount.objects.get_or_create(
                    assignee=user,
                    defaults={_count_field_for_type(t): 0 for t in TYPE_NAMES},
                )
                changed = False
                for type_name in TYPE_NAMES:
                    field = _count_field_for_type(type_name)
                    new_val = assigned_counts[type_name]
                    if getattr(obj, field) != new_val:
                        setattr(obj, field, new_val)
                        changed = True
                if changed and not dry_run:
                    obj.save()
                if changed or created:
                    updated_assigned += 1

                # CreatedTasksCount
                created_counts = created_by_user.get(username, _build_zero_counts())
                obj, created = CreatedTasksCount.objects.get_or_create(
                    creator=user,
                    defaults={_count_field_for_type(t): 0 for t in TYPE_NAMES},
                )
                changed = False
                for type_name in TYPE_NAMES:
                    field = _count_field_for_type(type_name)
                    new_val = created_counts[type_name]
                    if getattr(obj, field) != new_val:
                        setattr(obj, field, new_val)
                        changed = True
                if changed and not dry_run:
                    obj.save()
                if changed or created:
                    updated_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Refreshed task counts for {len(users)} user(s): "
                f"assigned rows touched={updated_assigned}, created rows touched={updated_created}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no database changes were made."))
