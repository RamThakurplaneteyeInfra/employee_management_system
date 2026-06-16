from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.leave_scoring import build_leave_points
from accounts.performance_scoring import build_performance_score
from accounts.models import (
    LeaveApplicationData,
    LeaveStatus,
    LeaveTypes,
    Profile,
    Roles,
)
from notifications.models import Notification


class LeaveNotificationFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.role_teamlead = Roles.objects.create(role_name="TeamLead")
        self.role_hr = Roles.objects.create(role_name="HR")
        self.role_md = Roles.objects.create(role_name="MD")

        self.pending = LeaveStatus.objects.create(name="Pending")
        self.approved = LeaveStatus.objects.create(name="Approved")
        self.rejected = LeaveStatus.objects.create(name="Rejected")

        self.full_day = LeaveTypes.objects.create(name="Full_day")
        self.short_leave = LeaveTypes.objects.create(name="Short Leave")

        self.emp = User.objects.create_user(username="EMP001", password="pass123")
        self.alt = User.objects.create_user(username="EMP002", password="pass123")
        self.tl = User.objects.create_user(username="TL001", password="pass123")
        self.hr = User.objects.create_user(username="HR001", password="pass123")
        self.md = User.objects.create_user(username="MD001", password="pass123")

        Profile.objects.create(
            Employee_id=self.tl,
            Role=self.role_teamlead,
            Name="Team Lead",
            Email_id="tl@example.com",
        )
        Profile.objects.create(
            Employee_id=self.hr,
            Role=self.role_hr,
            Name="HR User",
            Email_id="hr@example.com",
        )
        Profile.objects.create(
            Employee_id=self.md,
            Role=self.role_md,
            Name="MD User",
            Email_id="md@example.com",
        )
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Teamlead=self.tl,
            Name="Employee User",
            Email_id="emp@example.com",
        )
        Profile.objects.create(
            Employee_id=self.alt,
            Role=self.role_employee,
            Name="Alternative User",
            Email_id="alt@example.com",
        )

    def _create_regular_leave_with_alternative(self):
        self.client.force_authenticate(user=self.emp)
        payload = {
            "start_date": "2026-05-27",
            "duration_of_days": 1,
            "leave_subject": "Personal work",
            "reason": "Need day off",
            "leave_type": "Full_day",
            "alternative": self.alt.username,
        }
        response = self.client.post("/accounts/leave-applications/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        application_id = response.data["id"]
        return LeaveApplicationData.objects.get(pk=application_id)

    def test_submission_notifies_alternative_once(self):
        self._create_regular_leave_with_alternative()
        qs = Notification.objects.filter(receipient=self.alt)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().type_of_notification.type_name, "Leave_Submitted_Alternative")

    def test_alternative_approval_notifies_team_lead(self):
        app = self._create_regular_leave_with_alternative()

        self.client.force_authenticate(user=self.alt)
        response = self.client.patch(
            f"/accounts/leave-applications/{app.id}/",
            {"alternative_approval": "Approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        qs = Notification.objects.filter(receipient=self.tl, type_of_notification__type_name="Leave_Alternative_Approved")
        self.assertEqual(qs.count(), 1)

    def test_team_lead_approval_notifies_hr(self):
        app = self._create_regular_leave_with_alternative()
        self.client.force_authenticate(user=self.tl)
        response = self.client.patch(
            f"/accounts/leave-applications/{app.id}/",
            {"team_lead_approval": "Approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        qs = Notification.objects.filter(receipient=self.hr, type_of_notification__type_name="Leave_TeamLead_Approved")
        self.assertEqual(qs.count(), 1)

    def test_hr_approval_notifies_md(self):
        app = self._create_regular_leave_with_alternative()
        self.client.force_authenticate(user=self.hr)
        response = self.client.patch(
            f"/accounts/leave-applications/{app.id}/",
            {"HR_approval": "Approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        qs = Notification.objects.filter(receipient=self.md, type_of_notification__type_name="Leave_HR_Approved")
        self.assertEqual(qs.count(), 1)

    def test_md_approval_notifies_applicant(self):
        app = self._create_regular_leave_with_alternative()
        self.client.force_authenticate(user=self.md)
        response = self.client.patch(
            f"/accounts/leave-applications/{app.id}/",
            {"MD_approval": "Approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        qs = Notification.objects.filter(receipient=self.emp, type_of_notification__type_name="Leave_Final_Approved")
        self.assertEqual(qs.count(), 1)

    def test_repeated_same_approval_does_not_duplicate_notification(self):
        app = self._create_regular_leave_with_alternative()
        self.client.force_authenticate(user=self.alt)
        url = f"/accounts/leave-applications/{app.id}/"
        first = self.client.patch(url, {"alternative_approval": "Approved"}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        second = self.client.patch(url, {"alternative_approval": "Approved"}, format="json")
        self.assertEqual(second.status_code, 400, second.data)
        qs = Notification.objects.filter(
            receipient=self.tl,
            type_of_notification__type_name="Leave_Alternative_Approved",
        )
        self.assertEqual(qs.count(), 1)

    def test_missing_team_lead_falls_back_to_hr_after_alternative(self):
        app = self._create_regular_leave_with_alternative()
        app.team_lead = None
        app.save(update_fields=["team_lead"])

        self.client.force_authenticate(user=self.alt)
        response = self.client.patch(
            f"/accounts/leave-applications/{app.id}/",
            {"alternative_approval": "Approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        qs = Notification.objects.filter(
            receipient=self.hr,
            type_of_notification__type_name="Leave_TeamLead_Approved",
        )
        self.assertEqual(qs.count(), 1)

    def test_short_leave_does_not_trigger_regular_chain_submission_notification(self):
        self.client.force_authenticate(user=self.emp)
        payload = {
            "date": "2026-05-27",
            "short_leave_start_time": "10:00:00",
            "leave_subject": "Doctor visit",
            "reason": "Checkup",
        }
        response = self.client.post("/accounts/leave-applications/short/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            Notification.objects.filter(type_of_notification__type_name="Leave_Submitted_Alternative").count(),
            0,
        )


class LeaveScoringTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.approved = LeaveStatus.objects.create(name="Approved")
        self.pending = LeaveStatus.objects.create(name="Pending")
        self.full_day = LeaveTypes.objects.create(name="Full_day")
        self.half_day = LeaveTypes.objects.create(name="Half_day")
        self.emp = User.objects.create_user(username="EMP100", password="pass123")
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="Scoring Employee",
            Email_id="scoring@example.com",
        )

    def _create_leave(
        self,
        *,
        start_date,
        leave_type,
        applied_on=None,
        md_approved=True,
    ):
        applied_on = applied_on or start_date
        aware_applied = timezone.make_aware(datetime.combine(applied_on, time.min))
        return LeaveApplicationData.objects.create(
            applicant=self.emp,
            start_date=start_date,
            duration_of_days=1,
            leave_subject="Test leave",
            reason="Test reason",
            leave_type=leave_type,
            MD_approval=self.approved if md_approved else self.pending,
            application_date=applied_on,
            applied_at=aware_applied,
        )

    def test_allowance_uses_day_units_and_counts_show_totals(self):
        self._create_leave(start_date=date(2026, 6, 3), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 6, 10), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 6, 20), leave_type=self.full_day)

        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["points"]["full_day"], -3.0)
        self.assertEqual(result["total_points"], -1.0)
        self.assertEqual(result["counts"]["waived"], 2)
        self.assertEqual(result["counts"]["waived_units"], 2.0)
        self.assertEqual(result["counts"]["full_day"], 3)
        self.assertEqual(result["monthly_free_allowance"], 2.0)

    def test_two_half_days_and_one_full_day_use_full_allowance(self):
        self._create_leave(start_date=date(2026, 6, 3), leave_type=self.half_day)
        self._create_leave(start_date=date(2026, 6, 4), leave_type=self.half_day)
        self._create_leave(start_date=date(2026, 6, 5), leave_type=self.full_day)

        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["points"]["half_day"], -1.0)
        self.assertEqual(result["points"]["full_day"], -1.0)
        self.assertEqual(result["total_points"], 0.0)
        self.assertEqual(result["counts"]["half_day"], 2)
        self.assertEqual(result["counts"]["full_day"], 1)
        self.assertEqual(result["counts"]["waived"], 3)
        self.assertEqual(result["counts"]["waived_units"], 2.0)

    def test_mixed_month_pattern_matches_unit_allowance(self):
        self._create_leave(start_date=date(2026, 6, 1), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 6, 4), leave_type=self.half_day)
        self._create_leave(start_date=date(2026, 6, 5), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 6, 8), leave_type=self.half_day)

        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["points"]["half_day"], -1.0)
        self.assertEqual(result["points"]["full_day"], -2.0)
        self.assertEqual(result["total_points"], -1.0)
        self.assertEqual(result["counts"]["half_day"], 2)
        self.assertEqual(result["counts"]["full_day"], 2)
        self.assertEqual(result["counts"]["waived"], 3)
        self.assertEqual(result["counts"]["waived_units"], 2.0)

    def test_monthly_allowance_resets_each_calendar_month(self):
        self._create_leave(start_date=date(2026, 6, 28), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 6, 29), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 7, 1), leave_type=self.full_day)

        result = build_leave_points(self.emp, 2026)

        # Leaves only in June and July; other 10 months earn +2 bonus each.
        self.assertEqual(result["total_points"], 20.0)
        self.assertEqual(result["counts"]["waived"], 3)
        self.assertEqual(result["counts"]["full_day"], 3)
        self.assertEqual(result["counts"]["no_leave_months"], 10)

    def test_no_leave_month_earns_bonus(self):
        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["total_points"], 2.0)
        self.assertEqual(result["points"]["no_leave_bonus"], 2.0)
        self.assertEqual(result["counts"]["no_leave_months"], 1)
        self.assertEqual(result["no_leave_monthly_bonus"], 2.0)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["event_type"], "no_leave_bonus")

    def test_month_with_leaves_does_not_get_no_leave_bonus(self):
        self._create_leave(start_date=date(2026, 6, 5), leave_type=self.full_day)
        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["points"]["no_leave_bonus"], 0.0)
        self.assertEqual(result["counts"]["no_leave_months"], 0)

    def test_late_leave_uses_normal_allowance_while_unapproved_scoring_disabled(self):
        self._create_leave(start_date=date(2026, 6, 5), leave_type=self.full_day)
        self._create_leave(
            start_date=date(2026, 6, 12),
            leave_type=self.full_day,
            applied_on=date(2026, 6, 13),
        )

        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["total_points"], 0.0)
        self.assertEqual(result["counts"]["waived"], 2)
        self.assertEqual(result["counts"]["full_day"], 2)
        self.assertEqual(result["counts"]["unapproved_absent"], 0)


class PerformanceScoringTests(TestCase):
    def setUp(self):
        from events.models import BookSlot, BookingStatus, Room, SlotMembers

        self.BookSlot = BookSlot
        self.SlotMembers = SlotMembers
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.approved = LeaveStatus.objects.create(name="Approved")
        self.confirmed = BookingStatus.objects.create(status_name="Confirmed")
        self.full_day = LeaveTypes.objects.create(name="Full_day")
        self.indoor_room = Room.objects.create(name="Conference A")
        self.emp = User.objects.create_user(username="EMP300", password="pass123")
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="Performance Employee",
            Email_id="perf@example.com",
        )

    def test_combined_score_merges_leave_and_meeting(self):
        aware_applied = timezone.make_aware(datetime.combine(date(2026, 6, 1), time.min))
        LeaveApplicationData.objects.create(
            applicant=self.emp,
            start_date=date(2026, 6, 5),
            duration_of_days=1,
            leave_subject="Leave",
            reason="Reason",
            leave_type=self.full_day,
            MD_approval=self.approved,
            application_date=date(2026, 6, 1),
            applied_at=aware_applied,
        )
        slot = self.BookSlot.objects.create(
            meeting_title="Standup",
            date=date(2026, 6, 10),
            start_time=time(10, 0),
            end_time=time(11, 0),
            room=self.indoor_room,
            meeting_type="group",
            status=self.confirmed,
            created_by=self.emp,
        )
        self.SlotMembers.objects.create(slot=slot, member=self.emp)

        result = build_performance_score(self.emp, 2026, month=6)

        self.assertEqual(result["leave"]["total_points"], 0.0)
        self.assertEqual(result["meeting"]["total_points"], 0.25)
        self.assertEqual(result["checklist"]["total_points"], 0.0)
        self.assertEqual(result["certification"]["total_points"], 0.0)
        self.assertEqual(result["combined_total_points"], 0.25)
        self.assertIn("leave", result)
        self.assertIn("meeting", result)
        self.assertIn("checklist", result)
        self.assertIn("certification", result)
        self.assertEqual(result["employee_id"], "EMP300")


class CompletedYearsAndDaysTests(TestCase):
    def test_null_join_date_returns_none(self):
        from accounts.filters import completed_years_and_days

        self.assertIsNone(completed_years_and_days(None))

    def test_valid_join_date_returns_tenure_string(self):
        from accounts.filters import completed_years_and_days

        result = completed_years_and_days(date(2020, 1, 15))
        self.assertIn("years", result)
        self.assertIn("days", result)
