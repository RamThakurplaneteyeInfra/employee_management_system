from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Profile, Roles
from task_management.models import Task, TaskAssignies, TaskStatus, TaskTypes


class AiSummaryApiTests(APITestCase):
    def setUp(self) -> None:
        self.role_teamlead = Roles.objects.create(role_name="TeamLead", total_count=0)

        self.teamlead = User.objects.create_user(username="tl1", password="pass")
        Profile.objects.create(
            Employee_id=self.teamlead,
            Role=self.role_teamlead,
            Name="Team Lead 1",
            Email_id="tl1@example.com",
        )

        self.member = User.objects.create_user(username="mem1", password="pass")
        Profile.objects.create(
            Employee_id=self.member,
            Teamlead=self.teamlead,
            Name="Member 1",
            Email_id="mem1@example.com",
        )

        self.intern = User.objects.create_user(username="int1", password="pass")
        Profile.objects.create(
            Employee_id=self.intern,
            Name="Intern 1",
            Email_id="int1@example.com",
        )

        self.status_pending = TaskStatus.objects.create(status_name="PENDING")
        self.status_completed = TaskStatus.objects.create(status_name="COMPLETED")
        self.task_type = TaskTypes.objects.create(type_name="SOS")

        self.t1 = Task.objects.create(
            title="T1",
            description="d",
            created_by=self.intern,
            due_date=date.today(),
            type=self.task_type,
            status=self.status_pending,
        )
        TaskAssignies.objects.create(task=self.t1, assigned_to=self.intern)

        self.t2 = Task.objects.create(
            title="T2",
            description="d",
            created_by=self.teamlead,
            due_date=date.today(),
            type=self.task_type,
            status=self.status_completed,
        )
        TaskAssignies.objects.create(task=self.t2, assigned_to=self.member)

    @patch("ai_summary.views.generate_markdown_summary", return_value="**ok**")
    def test_run_intern_creates_row_and_returns_metrics(self, _mock):
        self.client.login(username="int1", password="pass")
        url = reverse("ai_summary_run")
        r = self.client.post(url, data={"type": "intern"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["type"], "intern")
        self.assertIn("metrics", r.data)
        self.assertEqual(r.data["summary"], "**ok**")
        self.assertEqual(r.data["metrics"]["tasks_total"], 1)
        self.assertEqual(r.data["metrics"]["tasks_pending"], 1)

    @patch("ai_summary.views.generate_markdown_summary", return_value="**ok**")
    def test_teamlead_requires_permission(self, _mock):
        self.client.login(username="int1", password="pass")
        url = reverse("ai_summary_run")
        r = self.client.post(url, data={"type": "teamlead"}, format="json")
        self.assertEqual(r.status_code, 403)

    @patch("ai_summary.views.generate_markdown_summary", return_value="**ok**")
    def test_run_teamlead_aggregates_team_tasks(self, _mock):
        self.client.login(username="tl1", password="pass")
        url = reverse("ai_summary_run")
        r = self.client.post(url, data={"type": "teamlead"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["metrics"]["tasks_total"], 1)
        self.assertEqual(r.data["metrics"]["tasks_completed"], 1)

    def test_latest_returns_null_when_missing(self):
        self.client.login(username="int1", password="pass")
        url = reverse("ai_summary_latest")
        r = self.client.get(url, data={"type": "intern"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["summary"], None)

