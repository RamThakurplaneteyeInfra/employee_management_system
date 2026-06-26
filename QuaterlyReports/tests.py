from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile, Roles, Functions
from QuaterlyReports.models import ActionableGoals, FunctionsEntries, FunctionsGoals
from task_management.models import TaskStatus


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


class ActionableEntriesCreatorScoringTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.creator = User.objects.create_user(username="creator_ae", password="pass")
        Profile.objects.create(
            Employee_id=self.creator,
            Role=self.role_employee,
            Name="Creator AE",
            Email_id="creator_ae@test.com",
        )
        self.completed = TaskStatus.objects.create(status_name="COMPLETED")
        self.pending = TaskStatus.objects.create(status_name="PENDING")
        self.npd = Functions.objects.create(function="NPD")

    def _create_entry(self, day, status):
        return FunctionsEntries.objects.create(
            Creator=self.creator,
            co_author=self.creator,
            approved_by_coauthor=True,
            date=date(2026, 6, day),
            final_Status=status,
            original_entry=f"Entry {day}",
        )

    def test_not_eligible_when_no_special_function(self):
        from QuaterlyReports.actionable_entries_scoring import build_actionable_entries_points

        self._create_entry(5, self.completed)
        result = build_actionable_entries_points(self.creator, 2026, month=6)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["total_points"], 0.0)

    def test_five_completed_hits_main_cap(self):
        from QuaterlyReports.actionable_entries_scoring import build_actionable_entries_points

        # Make creator eligible (NPD)
        profile = Profile.objects.get(Employee_id=self.creator)
        profile.functions.add(self.npd)

        for day in range(1, 6):  # 5 completed * 4 = 20
            self._create_entry(day, self.completed)
        result = build_actionable_entries_points(self.creator, 2026, month=6)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["main_score"], 20.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 20.0)

    def test_six_completed_adds_bonus(self):
        from QuaterlyReports.actionable_entries_scoring import build_actionable_entries_points

        profile = Profile.objects.get(Employee_id=self.creator)
        profile.functions.add(self.npd)

        for day in range(1, 7):  # 6 * 4 = 24 => 20 main + 4 bonus
            self._create_entry(day, self.completed)
        result = build_actionable_entries_points(self.creator, 2026, month=6)
        self.assertEqual(result["main_score"], 20.0)
        self.assertEqual(result["monthly_bonus"], 4.0)
        self.assertEqual(result["total_points"], 24.0)

    def test_points_endpoint(self):
        profile = Profile.objects.get(Employee_id=self.creator)
        profile.functions.add(self.npd)
        self._create_entry(5, self.completed)
        self.client = APIClient()
        self.client.force_authenticate(self.creator)
        r = self.client.get("/ActionableEntries/points/?year=2026&month=6")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["eligible"])
        self.assertEqual(r.data["total_points"], 4.0)


class NpcActionableEntryCreateTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.npc_user = User.objects.create_user(username="npc_emp", password="pass")
        self.npd_user = User.objects.create_user(username="npd_emp", password="pass")
        self.co_author = User.objects.create_user(username="co_npc", password="pass")
        self.share_with = User.objects.create_user(username="share_npc", password="pass")
        Profile.objects.create(
            Employee_id=self.npc_user,
            Role=self.role_employee,
            Name="NPC Employee",
            Email_id="npc@test.com",
        )
        Profile.objects.create(
            Employee_id=self.npd_user,
            Role=self.role_employee,
            Name="NPD Employee",
            Email_id="npd@test.com",
        )
        Profile.objects.create(
            Employee_id=self.co_author,
            Role=self.role_employee,
            Name="Co Author",
            Email_id="co@test.com",
        )
        Profile.objects.create(
            Employee_id=self.share_with,
            Role=self.role_employee,
            Name="Share User",
            Email_id="share@test.com",
        )
        npc_fn = Functions.objects.create(function="NPC")
        npd_fn = Functions.objects.create(function="NPD")
        Profile.objects.get(Employee_id=self.npc_user).functions.add(npc_fn)
        Profile.objects.get(Employee_id=self.npd_user).functions.add(npd_fn)
        self.npd_main_goal = FunctionsGoals.objects.create(Function=npd_fn, Maingoal="Catalog main")
        self.catalog_goal = ActionableGoals.objects.create(
            FunctionGoal=self.npd_main_goal,
            purpose="Predefined catalog goal",
        )
        TaskStatus.objects.get_or_create(status_name="PENDING")

    def test_npc_create_with_goal_text_succeeds(self):
        self.client = APIClient()
        self.client.force_authenticate(self.npc_user)
        payload = {
            "date": "2026-06-26",
            "original_entry": "Completed customer visit",
            "goal_text": "Expand Pune dealer network",
            "co_author": self.co_author.username,
            "share_with": self.share_with.username,
        }
        response = self.client.post("/ActionableEntries/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["goal_text"], "Expand Pune dealer network")
        self.assertIsNotNone(response.data["goal"])
        self.assertEqual(response.data["original_entry"], "Completed customer visit")

    def test_npc_create_accepts_goal_name_alias(self):
        self.client = APIClient()
        self.client.force_authenticate(self.npc_user)
        payload = {
            "date": "2026-06-26",
            "original_entry": "Work done",
            "goal_name": "Pipeline improvement",
            "co_author": self.co_author.username,
            "share_with": self.share_with.username,
        }
        response = self.client.post("/ActionableEntries/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["goal_text"], "Pipeline improvement")

    def test_non_npc_cannot_use_goal_text_without_catalog_goal(self):
        self.client = APIClient()
        self.client.force_authenticate(self.npd_user)
        payload = {
            "date": "2026-06-26",
            "original_entry": "Testing",
            "goal_text": "Should fail",
            "co_author": self.co_author.username,
            "share_with": self.share_with.username,
        }
        response = self.client.post("/ActionableEntries/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("goal_text", response.data)

    def test_npd_catalog_goal_create_unchanged(self):
        self.client = APIClient()
        self.client.force_authenticate(self.npd_user)
        payload = {
            "date": "2026-06-26",
            "original_entry": "Testing",
            "goal": self.catalog_goal.id,
            "co_author": self.co_author.username,
            "share_with": self.share_with.username,
        }
        response = self.client.post("/ActionableEntries/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["goal"], self.catalog_goal.id)
        self.assertEqual(response.data["goal_text"], "Predefined catalog goal")

    def test_npc_scoring_eligible_after_complete(self):
        from QuaterlyReports.actionable_entries_scoring import build_actionable_entries_points

        completed = TaskStatus.objects.create(status_name="COMPLETED")
        FunctionsEntries.objects.create(
            Creator=self.npc_user,
            co_author=self.co_author,
            approved_by_coauthor=True,
            date=date(2026, 6, 5),
            final_Status=completed,
            original_entry="Done",
        )
        result = build_actionable_entries_points(self.npc_user, 2026, month=6)
        self.assertTrue(result["eligible"])
        self.assertIn("NPC", result["eligible_functions"])
        self.assertEqual(result["total_points"], 4.0)
