from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

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
