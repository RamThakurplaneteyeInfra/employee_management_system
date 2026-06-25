from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.leave_scoring import build_leave_points
from accounts.performance_scoring import (
    build_org_average_performance_score,
    build_performance_score,
    build_performance_scores_list,
    classify_scoring_group,
    parse_scoring_group,
)
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
        self.assertEqual(result["total_points"], 7.2)
        self.assertEqual(result["points"]["base"], 8.0)
        self.assertEqual(result["points"]["total_deductions"], 0.8)
        self.assertEqual(result["counts"]["waived"], 2)
        self.assertEqual(result["counts"]["waived_units"], 2.0)
        self.assertEqual(result["counts"]["full_day"], 3)
        self.assertEqual(result["monthly_free_allowance"], 2.0)

    def test_two_half_days_and_one_full_day_use_full_allowance(self):
        self._create_leave(start_date=date(2026, 6, 3), leave_type=self.half_day)
        self._create_leave(start_date=date(2026, 6, 4), leave_type=self.half_day)
        self._create_leave(start_date=date(2026, 6, 5), leave_type=self.full_day)

        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["points"]["half_day"], -0.8)
        self.assertEqual(result["points"]["full_day"], -0.8)
        self.assertEqual(result["total_points"], 8.0)
        self.assertEqual(result["points"]["total_deductions"], 0.0)
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

        self.assertEqual(result["points"]["half_day"], -0.8)
        self.assertEqual(result["points"]["full_day"], -1.6)
        self.assertEqual(result["total_points"], 6.8)
        self.assertEqual(result["points"]["total_deductions"], 1.2)
        self.assertEqual(result["counts"]["half_day"], 2)
        self.assertEqual(result["counts"]["full_day"], 2)
        self.assertEqual(result["counts"]["waived"], 3)
        self.assertEqual(result["counts"]["waived_units"], 2.0)

    def test_monthly_allowance_resets_each_calendar_month(self):
        self._create_leave(start_date=date(2026, 6, 28), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 6, 29), leave_type=self.full_day)
        self._create_leave(start_date=date(2026, 7, 1), leave_type=self.full_day)

        result = build_leave_points(self.emp, 2026)

        # Leaves only in June and July (within allowance); other 10 months score full 8.
        self.assertEqual(result["total_points"], 96.0)
        self.assertEqual(result["max_points"], 96.0)
        self.assertEqual(result["counts"]["waived"], 3)
        self.assertEqual(result["counts"]["full_day"], 3)
        self.assertEqual(result["counts"]["full_score_months"], 12)

    def test_no_leave_month_scores_full_eight(self):
        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["total_points"], 8.0)
        self.assertEqual(result["points"]["base"], 8.0)
        self.assertEqual(result["points"]["total_deductions"], 0.0)
        self.assertEqual(result["counts"]["full_score_months"], 1)
        self.assertEqual(result["monthly_max_points"], 8.0)
        monthly_events = [e for e in result["events"] if e["event_type"] == "monthly_score"]
        self.assertEqual(len(monthly_events), 1)
        self.assertEqual(monthly_events[0]["remaining_points"], 8.0)

    def test_month_with_leaves_within_allowance_keeps_full_score(self):
        self._create_leave(start_date=date(2026, 6, 5), leave_type=self.full_day)
        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["total_points"], 8.0)
        self.assertEqual(result["points"]["total_deductions"], 0.0)
        self.assertEqual(result["counts"]["full_score_months"], 1)

    def test_late_leave_uses_normal_allowance_while_unapproved_scoring_disabled(self):
        self._create_leave(start_date=date(2026, 6, 5), leave_type=self.full_day)
        self._create_leave(
            start_date=date(2026, 6, 12),
            leave_type=self.full_day,
            applied_on=date(2026, 6, 13),
        )

        result = build_leave_points(self.emp, 2026, month=6)

        self.assertEqual(result["total_points"], 8.0)
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

        self.assertEqual(result["leave"]["total_points"], 8.0)
        self.assertEqual(result["meeting"]["total_points"], 0.25)
        self.assertEqual(result["checklist"]["total_points"], 0.0)
        self.assertEqual(result["certification"]["total_points"], 0.0)
        self.assertEqual(result["actionable_coauthor"]["total_points"], 0.0)
        self.assertEqual(result["actionable_entries"]["total_points"], 0.0)
        self.assertEqual(result["customer_panel_entries"]["total_points"], 0.0)
        self.assertEqual(result["combined_total_bonus"], 0.0)
        self.assertEqual(result["bonus_by_category"]["meeting"], 0.0)
        self.assertEqual(
            result["combined_total_points"],
            result["leave"]["total_points"] + result["meeting"]["main_score"],
        )
        self.assertEqual(result["scoring_profile"], "default")
        self.assertIn("leave", result)
        self.assertIn("meeting", result)
        self.assertIn("checklist", result)
        self.assertIn("certification", result)
        self.assertIn("actionable_coauthor", result)
        self.assertIn("actionable_entries", result)
        self.assertIn("customer_panel_entries", result)
        self.assertIn("client_profiles", result)
        self.assertIn("employee_functions", result)
        self.assertEqual(result["employee_functions"], [])
        self.assertEqual(result["employee_id"], "EMP300")
        self.assertEqual(result["months_in_period"], 1)
        for key in (
            "leave",
            "meeting",
            "checklist",
            "certification",
            "actionable_coauthor",
            "actionable_entries",
            "customer_panel_entries",
            "client_profiles",
        ):
            nested = result[key]
            self.assertNotIn("employee_id", nested)
            self.assertNotIn("period_type", nested)
            self.assertNotIn("months_in_period", nested)

    def test_standalone_leave_points_keeps_full_metadata(self):
        result = build_leave_points(self.emp, 2026, month=6)
        self.assertEqual(result["employee_id"], "EMP300")
        self.assertEqual(result["period_type"], "month")
        self.assertIn("months_in_period", result)


class MmrRgPerformanceScoreTests(TestCase):
    def setUp(self):
        from accounts.models import Functions
        from CustomerPanel.models import CustomerPanelEntry
        from datetime import datetime
        from decimal import Decimal

        self.Functions = Functions
        self.CustomerPanelEntry = CustomerPanelEntry
        self.Decimal = Decimal
        self.datetime = datetime

        self.role_employee = Roles.objects.create(role_name="Employee")
        self.approved = LeaveStatus.objects.create(name="Approved")
        self.full_day = LeaveTypes.objects.create(name="Full_day")
        self.emp = User.objects.create_user(username="MMR400", password="pass123")
        profile = Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="MMR Performance",
            Email_id="mmrperf@example.com",
        )
        self.mmr = Functions.objects.create(function="MMR")
        profile.functions.add(self.mmr)

    def test_mmr_combined_score_includes_meeting_and_client_profiles(self):
        from accounts.performance_scoring import build_performance_score
        from events.models import BookSlot, BookingStatus, Room, SlotMembers
        from Clients.models import ClientProfile, CurrentClientStage

        aware = timezone.make_aware(self.datetime.combine(date(2026, 6, 1), time.min))
        LeaveApplicationData.objects.create(
            applicant=self.emp,
            start_date=date(2026, 6, 5),
            duration_of_days=1,
            leave_subject="Leave",
            reason="Reason",
            leave_type=self.full_day,
            MD_approval=self.approved,
            application_date=date(2026, 6, 1),
            applied_at=aware,
        )
        confirmed = BookingStatus.objects.create(status_name="Confirmed")
        room = Room.objects.create(name="Conference A")
        slot = BookSlot.objects.create(
            meeting_title="Client review",
            date=date(2026, 6, 12),
            start_time=time(10, 0),
            end_time=time(11, 0),
            room=room,
            meeting_type="group",
            status=confirmed,
            created_by=self.emp,
        )
        SlotMembers.objects.create(slot=slot, member=self.emp)
        entry = self.CustomerPanelEntry.objects.create(
            business_name="Client A",
            division=self.CustomerPanelEntry.DIVISION_FARM,
            total=self.Decimal("250000"),
            created_by=self.emp,
        )
        self.CustomerPanelEntry.objects.filter(pk=entry.pk).update(
            created_at=timezone.make_aware(self.datetime(2026, 6, 10, 10, 0, 0))
        )
        leads, _ = CurrentClientStage.objects.get_or_create(name="Leads")
        for day in range(1, 6):
            profile = ClientProfile.objects.create(
                company_name=f"Biz {day}",
                client_name=f"Contact {day}",
                status=leads,
                created_by=self.emp,
            )
            ClientProfile.objects.filter(pk=profile.pk).update(
                created_at=timezone.make_aware(self.datetime(2026, 6, day, 10, 0, 0))
            )

        result = build_performance_score(self.emp, 2026, month=6)

        self.assertEqual(result["scoring_profile"], "mmr_rg")
        self.assertEqual(result["leave"]["total_points"], 8.0)
        self.assertEqual(result["meeting"]["total_points"], 0.25)
        self.assertEqual(result["checklist"]["total_points"], 0.0)
        self.assertEqual(result["client_profiles"]["total_points"], 10.0)
        self.assertEqual(result["customer_panel_entries"]["total_points"], 20.0)
        self.assertEqual(result["client_profiles"]["components"]["profile_count"]["main_score"], 10.0)
        self.assertEqual(
            result["combined_total_points"],
            result["leave"]["total_points"]
            + result["meeting"]["main_score"]
            + result["certification"]["main_score"]
            + result["actionable_coauthor"]["main_score"]
            + result["client_profiles"]["main_score"]
            + result["customer_panel_entries"]["main_score"],
        )
        self.assertEqual(result["combined_total_bonus"], 0.0)


class PerformanceScoresListTests(TestCase):
    def setUp(self):
        from accounts.models import Functions

        self.Functions = Functions
        self.client = APIClient()
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.role_hr = Roles.objects.create(role_name="HR")
        self.role_md = Roles.objects.create(role_name="MD")
        self.role_teamlead = Roles.objects.create(role_name="TeamLead")

        self.hr = User.objects.create_user(username="HR900", password="pass123")
        Profile.objects.create(
            Employee_id=self.hr,
            Role=self.role_hr,
            Name="HR List",
            Email_id="hrlist@example.com",
        )
        self.md = User.objects.create_user(username="MD900", password="pass123")
        Profile.objects.create(
            Employee_id=self.md,
            Role=self.role_md,
            Name="MD List",
            Email_id="mdlist@example.com",
        )
        self.tl = User.objects.create_user(username="TL900", password="pass123")
        Profile.objects.create(
            Employee_id=self.tl,
            Role=self.role_teamlead,
            Name="Team Lead",
            Email_id="tl900@example.com",
        )

        self.mmr_emp = User.objects.create_user(username="MMR900", password="pass123")
        mmr_profile = Profile.objects.create(
            Employee_id=self.mmr_emp,
            Role=self.role_employee,
            Name="MMR Employee",
            Email_id="mmr900@example.com",
        )
        mmr_profile.functions.add(Functions.objects.create(function="MMR"))

        self.npd_emp = User.objects.create_user(username="NPD900", password="pass123")
        npd_profile = Profile.objects.create(
            Employee_id=self.npd_emp,
            Role=self.role_employee,
            Name="NPD Employee",
            Email_id="npd900@example.com",
        )
        npd_profile.functions.add(Functions.objects.create(function="NPD"))

        self.npc_emp = User.objects.create_user(username="NPC900", password="pass123")
        npc_profile = Profile.objects.create(
            Employee_id=self.npc_emp,
            Role=self.role_employee,
            Name="NPC Employee",
            Email_id="npc900@example.com",
        )
        npc_profile.functions.add(Functions.objects.create(function="NPC"))

        self.intern_emp = User.objects.create_user(username="INT900", password="pass123")
        Profile.objects.create(
            Employee_id=self.intern_emp,
            Role=Roles.objects.create(role_name="Intern"),
            Name="Intern List",
            Email_id="intlist@example.com",
        )

        self.other_emp = User.objects.create_user(username="OTH900", password="pass123")
        Profile.objects.create(
            Employee_id=self.other_emp,
            Role=self.role_employee,
            Name="Other Employee",
            Email_id="oth900@example.com",
        )

    def test_classify_scoring_group_mutually_exclusive(self):
        self.assertEqual(classify_scoring_group({"MMR"}), "mmr_rg")
        self.assertEqual(classify_scoring_group({"RG"}), "mmr_rg")
        self.assertEqual(classify_scoring_group({"NPD", "MMR"}), "mmr_rg")
        self.assertEqual(classify_scoring_group({"NPD"}), "npd_hc_ip")
        self.assertEqual(classify_scoring_group({"HC", "IP"}), "npd_hc_ip")
        self.assertEqual(classify_scoring_group({"NPC"}), "npc")
        self.assertEqual(classify_scoring_group({"NPC", "P&S"}), "npc")
        self.assertEqual(classify_scoring_group({"NPD", "NPC"}), "npd_hc_ip")
        self.assertEqual(classify_scoring_group(set()), "other")
        self.assertEqual(classify_scoring_group({"P&S"}), "other")

    def test_parse_scoring_group_aliases(self):
        self.assertEqual(parse_scoring_group("mmr-rg"), "mmr_rg")
        self.assertEqual(parse_scoring_group("npd_hc_ip"), "npd_hc_ip")
        self.assertEqual(parse_scoring_group("npc"), "npc")
        self.assertEqual(parse_scoring_group("interns"), "interns")
        self.assertEqual(parse_scoring_group("intern"), "interns")
        self.assertEqual(parse_scoring_group("default"), "other")
        self.assertIsNone(parse_scoring_group(""))

    def test_build_performance_scores_list_filters_by_group(self):
        result = build_performance_scores_list(
            "mmr_rg",
            self.hr,
            lambda u: "HR",
            2026,
            month=6,
        )
        self.assertEqual(result["group"], "mmr_rg")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["employees"][0]["employee_id"], "MMR900")
        self.assertEqual(result["employees"][0]["scoring_group"], "mmr_rg")

        npd_result = build_performance_scores_list(
            "npd_hc_ip",
            self.hr,
            lambda u: "HR",
            2026,
            month=6,
        )
        self.assertEqual(npd_result["count"], 1)
        self.assertEqual(npd_result["employees"][0]["employee_id"], "NPD900")

        npc_result = build_performance_scores_list(
            "npc",
            self.hr,
            lambda u: "HR",
            2026,
            month=6,
        )
        self.assertEqual(npc_result["count"], 1)
        self.assertEqual(npc_result["employees"][0]["employee_id"], "NPC900")
        self.assertEqual(npc_result["employees"][0]["scoring_group"], "npc")

        other_result = build_performance_scores_list(
            "other",
            self.hr,
            lambda u: "HR",
            2026,
            month=6,
        )
        self.assertEqual(other_result["count"], 1)
        self.assertEqual(other_result["employees"][0]["employee_id"], "OTH900")

        interns_result = build_performance_scores_list(
            "interns",
            self.hr,
            lambda u: "HR",
            2026,
            month=6,
        )
        self.assertEqual(interns_result["count"], 1)
        self.assertEqual(interns_result["employees"][0]["employee_id"], "INT900")
        self.assertEqual(interns_result["employees"][0]["scoring_profile"], "intern")

    def test_performance_scores_api_requires_group(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(
            "/accounts/leave-applications/performance-scores/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 400)

    def test_performance_scores_api_mmr_rg_shortcut(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(
            "/accounts/leave-applications/performance-scores/mmr-rg/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["group"], "mmr_rg")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["employees"][0]["employee_id"], "MMR900")
        self.assertIn("combined_total_points", response.data["employees"][0])

    def test_performance_scores_api_npc_shortcut(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(
            "/accounts/leave-applications/performance-scores/npc/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["group"], "npc")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["employees"][0]["employee_id"], "NPC900")

    def test_performance_scores_api_interns_shortcut(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(
            "/accounts/leave-applications/performance-scores/interns/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["group"], "interns")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["employees"][0]["employee_id"], "INT900")
        self.assertEqual(response.data["employees"][0]["scoring_profile"], "intern")

    def test_performance_scores_api_allowed_for_md(self):
        self.client.force_authenticate(user=self.md)
        response = self.client.get(
            "/accounts/leave-applications/performance-scores/other/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["group"], "other")

    def test_performance_scores_api_forbidden_for_teamlead(self):
        self.client.force_authenticate(user=self.tl)
        response = self.client.get(
            "/accounts/leave-applications/performance-scores/other/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 403)

    def test_performance_scores_api_forbidden_for_employee(self):
        self.client.force_authenticate(user=self.other_emp)
        response = self.client.get(
            "/accounts/leave-applications/performance-scores/other/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 403)


class HrOrgAveragePerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.role_hr = Roles.objects.create(role_name="HR")
        self.role_md = Roles.objects.create(role_name="MD")
        self.role_teamlead = Roles.objects.create(role_name="TeamLead")

        self.hr = User.objects.create_user(username="HRAVG", password="pass123")
        Profile.objects.create(
            Employee_id=self.hr,
            Role=self.role_hr,
            Name="HR Average",
            Email_id="hravg@example.com",
        )
        self.md = User.objects.create_user(username="MDAVG", password="pass123")
        Profile.objects.create(
            Employee_id=self.md,
            Role=self.role_md,
            Name="MD Average",
            Email_id="mdavg@example.com",
        )

        self.emp_a = User.objects.create_user(username="EMPAVG1", password="pass123")
        Profile.objects.create(
            Employee_id=self.emp_a,
            Role=self.role_employee,
            Name="Employee A",
            Email_id="empa@example.com",
        )
        self.emp_b = User.objects.create_user(username="EMPAVG2", password="pass123")
        Profile.objects.create(
            Employee_id=self.emp_b,
            Role=self.role_employee,
            Name="Employee B",
            Email_id="empb@example.com",
        )

    def _pool_combined_average(self, year=2026, month=6):
        pool_users = [self.emp_a, self.emp_b]
        totals = [
            build_performance_score(user, year, month=month)["combined_total_points"]
            for user in pool_users
        ]
        return round(sum(totals) / len(totals), 2), len(totals)

    def test_hr_score_is_org_average_excluding_hr_and_md(self):
        expected_avg, expected_count = self._pool_combined_average()
        result = build_performance_score(self.hr, 2026, month=6)

        self.assertEqual(result["scoring_profile"], "hr_org_average")
        self.assertEqual(result["combined_total_points"], expected_avg)
        self.assertEqual(result["derived_from_employee_count"], expected_count)
        self.assertIn("HR", result["excluded_roles"])

    def test_build_org_average_performance_score(self):
        expected_avg, expected_count = self._pool_combined_average()
        org = build_org_average_performance_score(2026, month=6)

        self.assertEqual(org["scoring_profile"], "hr_org_average")
        self.assertEqual(org["average_combined_total_points"], expected_avg)
        self.assertEqual(org["employee_count"], expected_count)

    def test_hr_performance_score_api(self):
        expected_avg, _ = self._pool_combined_average()
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(
            "/accounts/leave-applications/performance-score/",
            {"year": 2026, "month": 6, "employee": "HRAVG"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scoring_profile"], "hr_org_average")
        self.assertEqual(response.data["combined_total_points"], expected_avg)

    def test_hr_average_endpoint_for_hr_and_md(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(
            "/accounts/leave-applications/performance-score/hr-average/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scoring_profile"], "hr_org_average")
        self.assertIn("average_combined_total_points", response.data)

    def test_hr_average_endpoint_forbidden_for_employee(self):
        self.client.force_authenticate(user=self.emp_a)
        response = self.client.get(
            "/accounts/leave-applications/performance-score/hr-average/",
            {"year": 2026, "month": 6},
        )
        self.assertEqual(response.status_code, 403)


class InternTaskScoringTests(TestCase):
    def setUp(self):
        from decimal import Decimal

        from task_management.models import Task, TaskStatus, TaskStatusChangeLogs, TaskTypes

        self.Decimal = Decimal
        self.Task = Task
        self.TaskStatus = TaskStatus
        self.TaskStatusChangeLogs = TaskStatusChangeLogs
        self.TaskTypes = TaskTypes

        self.role_intern = Roles.objects.create(role_name="Intern")
        self.role_employee = Roles.objects.create(role_name="Employee")

        self.intern = User.objects.create_user(username="INT900", password="pass123")
        Profile.objects.create(
            Employee_id=self.intern,
            Role=self.role_intern,
            Name="Intern Scoring",
            Email_id="int900@example.com",
        )

        self.employee = User.objects.create_user(username="EMP900", password="pass123")
        Profile.objects.create(
            Employee_id=self.employee,
            Role=self.role_employee,
            Name="Employee Scoring",
            Email_id="emp900@example.com",
        )

        self.completed_status, _ = TaskStatus.objects.get_or_create(status_name="COMPLETED")
        self.task_type, _ = TaskTypes.objects.get_or_create(type_name="1 Day")

    def _create_completed_task(self, creator, *, completed_at):
        task = self.Task.objects.create(
            title=f"Task {creator.username}-{completed_at}",
            created_by=creator,
            due_date=date(2026, 6, 30),
            type=self.task_type,
            status=self.completed_status,
        )
        log = self.TaskStatusChangeLogs.objects.create(
            task=task,
            status_change_to=self.completed_status,
        )
        self.TaskStatusChangeLogs.objects.filter(pk=log.pk).update(last_edit=completed_at)
        return task

    def test_intern_21_tasks_full_main_score(self):
        from task_management.intern_task_scoring import build_intern_task_points

        completed_at = timezone.make_aware(datetime(2026, 6, 15, 10, 0, 0))
        for _ in range(21):
            self._create_completed_task(self.intern, completed_at=completed_at)

        result = build_intern_task_points(self.intern, 2026, month=6)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["counts"]["completed_tasks"], 21)
        self.assertEqual(result["main_score"], 70.0)
        self.assertEqual(result["monthly_bonus"], 0.0)

    def test_intern_extra_tasks_add_bonus(self):
        from task_management.intern_task_scoring import (
            MONTHLY_MAX_MAIN_POINTS,
            MONTHLY_TARGET_TASKS,
            build_intern_task_points,
        )

        completed_at = timezone.make_aware(datetime(2026, 6, 20, 10, 0, 0))
        for _ in range(25):
            self._create_completed_task(self.intern, completed_at=completed_at)

        result = build_intern_task_points(self.intern, 2026, month=6)
        expected_bonus = float(
            (self.Decimal(25) - self.Decimal(MONTHLY_TARGET_TASKS))
            * (MONTHLY_MAX_MAIN_POINTS / self.Decimal(MONTHLY_TARGET_TASKS))
        )
        self.assertEqual(result["main_score"], 70.0)
        self.assertAlmostEqual(result["monthly_bonus"], round(expected_bonus, 2))

    def test_non_intern_not_eligible(self):
        from task_management.intern_task_scoring import build_intern_task_points

        result = build_intern_task_points(self.employee, 2026, month=6)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["main_score"], 0.0)

    def test_intern_performance_score_uses_tasks_not_checklist(self):
        from task_management.intern_task_scoring import build_intern_task_points

        completed_at = timezone.make_aware(datetime(2026, 6, 10, 10, 0, 0))
        for _ in range(21):
            self._create_completed_task(self.intern, completed_at=completed_at)

        tasks_only = build_intern_task_points(self.intern, 2026, month=6)
        result = build_performance_score(self.intern, 2026, month=6)

        self.assertEqual(result["scoring_profile"], "intern")
        self.assertFalse(result["checklist"]["eligible"])
        self.assertEqual(result["checklist"]["main_score"], 0.0)
        self.assertEqual(result["tasks"]["main_score"], tasks_only["main_score"])
        expected_combined = round(
            result["leave"]["total_points"]
            + result["meeting"]["main_score"]
            + result["tasks"]["main_score"]
            + result["certification"]["main_score"]
            + result["actionable_coauthor"]["main_score"]
            + result["actionable_entries"]["main_score"],
            2,
        )
        self.assertEqual(result["combined_total_points"], expected_combined)


class MmrRgScoringTargetTests(TestCase):
    def setUp(self):
        from decimal import Decimal

        from accounts.models import Functions, MmrRgScoringTarget

        self.Decimal = Decimal
        self.MmrRgScoringTarget = MmrRgScoringTarget
        self.client = APIClient()
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.role_md = Roles.objects.create(role_name="MD")
        self.role_hr = Roles.objects.create(role_name="HR")

        self.md = User.objects.create_user(username="MDTGT", password="pass123")
        Profile.objects.create(
            Employee_id=self.md,
            Role=self.role_md,
            Name="MD Targets",
            Email_id="mdtgt@example.com",
        )
        self.hr = User.objects.create_user(username="HRTGT", password="pass123")
        Profile.objects.create(
            Employee_id=self.hr,
            Role=self.role_hr,
            Name="HR Targets",
            Email_id="hrtgt@example.com",
        )

        self.mmr_emp = User.objects.create_user(username="MMRTGT", password="pass123")
        mmr_profile = Profile.objects.create(
            Employee_id=self.mmr_emp,
            Role=self.role_employee,
            Name="MMR Target Employee",
            Email_id="mmrtgt@example.com",
        )
        mmr_profile.functions.add(Functions.objects.create(function="MMR"))

    def test_custom_customer_panel_target_changes_score(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points
        from CustomerPanel.models import CustomerPanelEntry
        from datetime import datetime

        self.MmrRgScoringTarget.objects.create(
            profile=self.mmr_emp.accounts_profile,
            year=2026,
            month=6,
            customer_panel_target_amount=self.Decimal("700000"),
            set_by=self.md,
        )
        entry = CustomerPanelEntry.objects.create(
            business_name="Client A",
            division=CustomerPanelEntry.DIVISION_FARM,
            total=self.Decimal("350000"),
            created_by=self.mmr_emp,
        )
        CustomerPanelEntry.objects.filter(pk=entry.pk).update(
            created_at=timezone.make_aware(datetime(2026, 6, 10, 10, 0, 0))
        )

        result = build_customer_panel_entries_points(self.mmr_emp, 2026, month=6)
        self.assertTrue(result["target_is_customized"])
        self.assertEqual(result["monthly_target_amount"], 700000.0)
        self.assertEqual(result["main_score"], 20.0)

    def test_yearly_scoring_uses_month_specific_targets(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points
        from CustomerPanel.models import CustomerPanelEntry
        from datetime import datetime

        self.MmrRgScoringTarget.objects.create(
            profile=self.mmr_emp.accounts_profile,
            year=2026,
            month=1,
            customer_panel_target_amount=self.Decimal("500000"),
            set_by=self.md,
        )
        self.MmrRgScoringTarget.objects.create(
            profile=self.mmr_emp.accounts_profile,
            year=2026,
            month=2,
            customer_panel_target_amount=self.Decimal("700000"),
            set_by=self.md,
        )
        for month, amount in ((1, "500000"), (2, "350000")):
            entry = CustomerPanelEntry.objects.create(
                business_name=f"Client {month}",
                division=CustomerPanelEntry.DIVISION_FARM,
                total=self.Decimal(amount),
                created_by=self.mmr_emp,
            )
            CustomerPanelEntry.objects.filter(pk=entry.pk).update(
                created_at=timezone.make_aware(datetime(2026, month, 10, 10, 0, 0))
            )

        result = build_customer_panel_entries_points(self.mmr_emp, 2026)
        self.assertEqual(result["main_score"], 60.0)

    def test_md_can_set_targets(self):
        self.client.force_authenticate(user=self.md)
        response = self.client.put(
            "/accounts/mmr-rg-scoring-targets/MMRTGT/?year=2026&month=6",
            {
                "customer_panel_target_amount": 700000,
                "proposal_target_amount": 6000000,
                "profile_count_target": 6,
                "proforma_target_amount": 1200000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_customized"])
        self.assertEqual(response.data["year"], 2026)
        self.assertEqual(response.data["month"], 6)
        self.assertEqual(
            response.data["effective_targets"]["customer_panel_target_amount"],
            700000.0,
        )

    def test_hr_can_list_but_not_set_targets(self):
        self.client.force_authenticate(user=self.hr)
        list_response = self.client.get("/accounts/mmr-rg-scoring-targets/?year=2026&month=6")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)

        write_response = self.client.patch(
            "/accounts/mmr-rg-scoring-targets/MMRTGT/?year=2026&month=6",
            {"customer_panel_target_amount": 700000},
            format="json",
        )
        self.assertEqual(write_response.status_code, 403)

    def test_reset_restores_defaults(self):
        self.MmrRgScoringTarget.objects.create(
            profile=self.mmr_emp.accounts_profile,
            year=2026,
            month=6,
            customer_panel_target_amount=self.Decimal("700000"),
            set_by=self.md,
        )
        self.client.force_authenticate(user=self.md)
        response = self.client.delete("/accounts/mmr-rg-scoring-targets/MMRTGT/reset/?year=2026&month=6")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_customized"])
        self.assertEqual(
            response.data["effective_targets"]["customer_panel_target_amount"],
            500000.0,
        )


    def test_list_requires_year_and_month(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get("/accounts/mmr-rg-scoring-targets/")
        self.assertEqual(response.status_code, 400)


class CompletedYearsAndDaysTests(TestCase):
    def test_null_join_date_returns_none(self):
        from accounts.filters import completed_years_and_days

        self.assertIsNone(completed_years_and_days(None))

    def test_valid_join_date_returns_tenure_string(self):
        from accounts.filters import completed_years_and_days

        result = completed_years_and_days(date(2020, 1, 15))
        self.assertIn("years", result)
        self.assertIn("days", result)
