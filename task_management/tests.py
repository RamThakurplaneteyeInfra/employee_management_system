from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.models import Profile, Roles
from task_management.filters import _get_tasks_by_type_sync
from task_management.models import Task, TaskAssignies, TaskStatus, TaskTypes

User = get_user_model()


class TaskListMonthFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.role = Roles.objects.create(role_name="Employee")
        self.creator = User.objects.create_user(username="TASKCRT", password="pass123")
        Profile.objects.create(
            Employee_id=self.creator,
            Role=self.role,
            Name="Task Creator",
            Email_id="taskcrt@example.com",
        )
        self.assignee = User.objects.create_user(username="TASKASN", password="pass123")
        Profile.objects.create(
            Employee_id=self.assignee,
            Role=self.role,
            Name="Task Assignee",
            Email_id="taskasn@example.com",
        )
        self.pending_status, _ = TaskStatus.objects.get_or_create(status_name="PENDING")
        self.task_type, _ = TaskTypes.objects.get_or_create(type_name="1 Day")

    def _request(self, path, params):
        request = self.factory.get(path, params)
        request.user = self.creator
        return request

    def _create_task(self, *, title, created_at, creator=None, assignee=None):
        task = Task.objects.create(
            title=title,
            created_by=creator or self.creator,
            due_date=date(2026, 6, 30),
            type=self.task_type,
            status=self.pending_status,
        )
        Task.objects.filter(pk=task.pk).update(created_at=created_at)
        if assignee is not None:
            TaskAssignies.objects.create(task=task, assigned_to=assignee)
        return task

    def test_without_month_returns_all_created_tasks(self):
        june = timezone.make_aware(datetime(2026, 6, 10, 12, 0, 0))
        may = timezone.make_aware(datetime(2026, 5, 10, 12, 0, 0))
        self._create_task(title="June task", created_at=june)
        self._create_task(title="May task", created_at=may)

        response = _get_tasks_by_type_sync(self._request("/tasks/viewTasks/", {}))
        titles = {item["Title"] for item in response}
        self.assertEqual(titles, {"June task", "May task"})

    def test_month_filter_limits_to_ist_created_at_month(self):
        june = timezone.make_aware(datetime(2026, 6, 10, 12, 0, 0))
        may = timezone.make_aware(datetime(2026, 5, 10, 12, 0, 0))
        self._create_task(title="June task", created_at=june)
        self._create_task(title="May task", created_at=may)

        response = _get_tasks_by_type_sync(
            self._request("/tasks/viewTasks/", {"month": "6", "year": "2026"})
        )
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["Title"], "June task")

    def test_month_defaults_year_to_current_when_omitted(self):
        now = timezone.localtime()
        created_at = timezone.make_aware(datetime(now.year, now.month, 15, 12, 0, 0))
        self._create_task(title="Current month task", created_at=created_at)

        response = _get_tasks_by_type_sync(
            self._request("/tasks/viewTasks/", {"month": str(now.month)})
        )
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["Title"], "Current month task")

    def test_pagination_returns_wrapped_response(self):
        june = timezone.make_aware(datetime(2026, 6, 10, 12, 0, 0))
        for i in range(3):
            self._create_task(title=f"Task {i}", created_at=june)

        response = _get_tasks_by_type_sync(
            self._request(
                "/tasks/viewTasks/",
                {"month": "6", "year": "2026", "limit": "2", "offset": "0"},
            )
        )
        self.assertIn("items", response)
        self.assertIn("pagination", response)
        self.assertEqual(len(response["items"]), 2)
        self.assertEqual(response["pagination"]["total"], 3)
        self.assertTrue(response["pagination"]["has_next"])
        self.assertFalse(response["pagination"]["has_prev"])

    def test_assigned_tasks_respect_month_filter(self):
        june = timezone.make_aware(datetime(2026, 6, 10, 12, 0, 0))
        may = timezone.make_aware(datetime(2026, 5, 10, 12, 0, 0))
        other = User.objects.create_user(username="OTHER", password="pass123")
        Profile.objects.create(
            Employee_id=other,
            Role=self.role,
            Name="Other Creator",
            Email_id="other@example.com",
        )
        self._create_task(title="June assigned", created_at=june, creator=other, assignee=self.creator)
        self._create_task(title="May assigned", created_at=may, creator=other, assignee=self.creator)

        request = self.factory.get(
            "/tasks/viewAssignedTasks/",
            {"month": "6", "year": "2026"},
        )
        request.user = self.creator
        response = _get_tasks_by_type_sync(request, self_created=False)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["Title"], "June assigned")
