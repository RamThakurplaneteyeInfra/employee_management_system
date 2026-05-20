from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile, Roles

from .models import TourAdvanceAttachment, TourAdvanceMember, TourAdvanceRequest
from .s3_helpers import is_allowed_s3_key, normalize_s3_key_from_client


class TourAdvanceVisibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_emp, _ = Roles.objects.get_or_create(role_name="Employee")
        self.role_admin, _ = Roles.objects.get_or_create(role_name="Admin")

        self.admin_user = User.objects.create_user(username="ta_admin", password="pass")
        self.creator = User.objects.create_user(username="ta_creator", password="pass")
        self.member_b = User.objects.create_user(username="ta_member_b", password="pass")
        self.other = User.objects.create_user(username="ta_other", password="pass")

        Profile.objects.create(
            Employee_id=self.admin_user,
            Name="TA Admin",
            Email_id="ta_admin@test.com",
            Role=self.role_admin,
        )
        Profile.objects.create(
            Employee_id=self.creator,
            Name="TA Creator",
            Email_id="ta_creator@test.com",
            Role=self.role_emp,
        )
        Profile.objects.create(
            Employee_id=self.member_b,
            Name="TA Member B",
            Email_id="ta_member_b@test.com",
            Role=self.role_emp,
        )
        Profile.objects.create(
            Employee_id=self.other,
            Name="TA Other",
            Email_id="ta_other@test.com",
            Role=self.role_emp,
        )

        self.req = TourAdvanceRequest.objects.create(
            tour_type="Client",
            primary_employee=self.creator,
            created_by=self.creator,
            advance=Decimal("1000.00"),
        )
        TourAdvanceMember.objects.create(request=self.req, member=self.creator)
        TourAdvanceMember.objects.create(request=self.req, member=self.member_b)

    def test_member_b_sees_request(self):
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/tour-advance/requests/")
        self.assertEqual(resp.status_code, 200)
        ids = [r["id"] for r in resp.data]
        self.assertIn(self.req.id, ids)

    def test_other_does_not_see_request(self):
        self.client.force_authenticate(user=self.other)
        resp = self.client.get("/api/tour-advance/requests/")
        self.assertEqual(resp.status_code, 200)
        ids = [r["id"] for r in resp.data]
        self.assertNotIn(self.req.id, ids)

    def test_admin_sees_all(self):
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.get("/api/tour-advance/requests/")
        self.assertEqual(resp.status_code, 200)
        ids = [r["id"] for r in resp.data]
        self.assertIn(self.req.id, ids)

    def test_list_all_admin_only(self):
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.get("/api/tour-advance/requests/all/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.req.id, [r["id"] for r in resp.data])

        self.client.force_authenticate(user=self.other)
        resp = self.client.get("/api/tour-advance/requests/all/")
        self.assertEqual(resp.status_code, 403)

    def test_list_my_scoped(self):
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/tour-advance/requests/my/")
        self.assertEqual(resp.status_code, 200)
        ids = [r["id"] for r in resp.data]
        self.assertIn(self.req.id, ids)

        self.client.force_authenticate(user=self.other)
        resp = self.client.get("/api/tour-advance/requests/my/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(self.req.id, [r["id"] for r in resp.data])

    def test_delete_disabled(self):
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.delete(f"/api/tour-advance/requests/{self.req.id}/")
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(TourAdvanceRequest.objects.filter(pk=self.req.pk).exists())

    def test_s3_key_validation(self):
        self.assertTrue(
            is_allowed_s3_key("Attachment/TourAdvance/abc123.pdf")
        )
        self.assertTrue(
            is_allowed_s3_key("Billing_Attachment/abc123.pdf")
        )
        self.assertTrue(
            is_allowed_s3_key(
                "https://ems-storage-123.s3.ap-south-1.amazonaws.com/"
                "Billing_Attachment/abc123.pdf"
            )
        )
        self.assertEqual(
            normalize_s3_key_from_client(
                "https://ems-storage-123.s3.ap-south-1.amazonaws.com/"
                "Billing_Attachment/abc123.pdf"
            ),
            "Billing_Attachment/abc123.pdf",
        )
        self.assertFalse(is_allowed_s3_key("../../../etc/passwd"))
        self.assertFalse(is_allowed_s3_key("events/tour/file.pdf"))
        self.assertFalse(is_allowed_s3_key("Attachment/Bill/abc123.pdf"))

    def test_update_with_attachments_preserves_existing(self):
        legacy_key = "Attachment/TourAdvance/existing.pdf"
        TourAdvanceAttachment.objects.create(
            request=self.req,
            s3_key=legacy_key,
            file_name="existing.pdf",
            amount=Decimal("100.00"),
        )
        new_key = "Billing_Attachment/newfile.pdf"
        self.client.force_authenticate(user=self.creator)
        resp = self.client.patch(
            f"/api/tour-advance/requests/{self.req.id}/",
            {
                "advance": "1200.00",
                "attachments": [
                    {
                        "fileUrl": new_key,
                        "fileName": "new.pdf",
                        "amount": "250.50",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        keys = {a["s3Key"] for a in resp.data["attachments"]}
        self.assertIn(legacy_key, keys)
        self.assertIn(new_key, keys)
        amounts = {a["s3Key"]: a["amount"] for a in resp.data["attachments"]}
        self.assertEqual(amounts[legacy_key], "100.00")
        self.assertEqual(amounts[new_key], "250.50")

    def test_update_ignores_employee_ids_for_non_admin(self):
        self.client.force_authenticate(user=self.creator)
        resp = self.client.patch(
            f"/api/tour-advance/requests/{self.req.id}/",
            {
                "advance": "1100.00",
                "employeeIds": ["ta_creator", "ta_member_b"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["advance"], "1100.00")
        self.assertIn("ta_member_b", resp.data["employeeIds"])

    def test_update_ignores_employee_id_for_non_admin(self):
        """Creator may resubmit full form including employeeId; primary stays unchanged."""
        self.client.force_authenticate(user=self.creator)
        resp = self.client.patch(
            f"/api/tour-advance/requests/{self.req.id}/",
            {
                "advance": "1050.00",
                "employeeId": "ta_member_b",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["advance"], "1050.00")
        self.assertEqual(resp.data["employeeId"], "ta_creator")

    def test_employee_create_with_other_members_via_api(self):
        self.client.force_authenticate(user=self.creator)
        resp = self.client.post(
            "/api/tour-advance/requests/",
            {
                "tourType": "Client",
                "advance": "2000.00",
                "employeeId": "ta_creator",
                "employeeIds": ["ta_creator", "ta_member_b"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        new_id = resp.data["id"]
        self.assertIn("ta_member_b", resp.data["employeeIds"])

        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/tour-advance/requests/my/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(new_id, [r["id"] for r in resp.data])

        self.client.force_authenticate(user=self.other)
        resp = self.client.get("/api/tour-advance/requests/my/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(new_id, [r["id"] for r in resp.data])

    def test_employee_create_for_other_primary_employee(self):
        self.client.force_authenticate(user=self.creator)
        resp = self.client.post(
            "/api/tour-advance/requests/",
            {
                "advance": "1500.00",
                "employeeId": "ta_member_b",
                "employeeIds": ["ta_member_b"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["employeeId"], "ta_member_b")
