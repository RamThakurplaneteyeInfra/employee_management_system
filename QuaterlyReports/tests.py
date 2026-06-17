from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile, Roles
from QuaterlyReports.models import FunctionsEntries


class ActionableCoauthorScoringTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.creator = User.objects.create_user(username="creator_ac", password="pass")
        self.coauthor = User.objects.create_user(username="coauthor_ac", password="pass")
        Profile.objects.create(
            Employee_id=self.creator,
            Role=self.role_employee,
            Name="Creator AC",
            Email_id="creator_ac@test.com",
        )
        Profile.objects.create(
            Employee_id=self.coauthor,
            Role=self.role_employee,
            Name="Coauthor AC",
            Email_id="coauthor_ac@test.com",
        )

    def _create_approved_entry(self, day):
        return FunctionsEntries.objects.create(
            Creator=self.creator,
            co_author=self.coauthor,
            approved_by_coauthor=True,
            date=date(2026, 6, day),
            original_entry=f"Entry {day}",
        )

    def test_three_approvals_all_main(self):
        from QuaterlyReports.actionable_coauthor_scoring import build_actionable_coauthor_points

        for day in (5, 10, 15):
            self._create_approved_entry(day)
        result = build_actionable_coauthor_points(self.coauthor, 2026, month=6)

        self.assertEqual(result["main_score"], 6.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 6.0)
        self.assertEqual(result["counts"]["approved_entries"], 3)
        self.assertTrue(all(e["points_type"] == "main" for e in result["events"]))

    def test_six_approvals_main_capped_with_bonus(self):
        from QuaterlyReports.actionable_coauthor_scoring import build_actionable_coauthor_points

        for day in range(1, 7):
            self._create_approved_entry(day)
        result = build_actionable_coauthor_points(self.coauthor, 2026, month=6)

        self.assertEqual(result["main_score"], 10.0)
        self.assertEqual(result["monthly_bonus"], 2.0)
        self.assertEqual(result["total_points"], 12.0)
        self.assertEqual(result["counts"]["approved_entries"], 6)
        main_events = [e for e in result["events"] if e["points_type"] == "main"]
        bonus_events = [e for e in result["events"] if e["points_type"] == "bonus"]
        self.assertEqual(len(main_events), 5)
        self.assertEqual(len(bonus_events), 1)

    def test_unapproved_entry_not_counted(self):
        from QuaterlyReports.actionable_coauthor_scoring import build_actionable_coauthor_points

        FunctionsEntries.objects.create(
            Creator=self.creator,
            co_author=self.coauthor,
            approved_by_coauthor=False,
            date=date(2026, 6, 5),
            original_entry="Pending",
        )
        result = build_actionable_coauthor_points(self.coauthor, 2026, month=6)
        self.assertEqual(result["total_points"], 0.0)

    def test_co_author_points_endpoint(self):
        self._create_approved_entry(5)
        for day in range(6, 11):
            self._create_approved_entry(day)
        self.client = APIClient()
        self.client.force_authenticate(self.coauthor)
        r = self.client.get("/ActionableEntriesCoAuthor/points/?year=2026&month=6")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["main_score"], 10.0)
        self.assertEqual(r.data["monthly_bonus"], 0.0)
        self.assertEqual(r.data["total_points"], 10.0)
