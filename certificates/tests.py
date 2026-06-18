from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile, Roles

from .models import EmployeeCertificate


class CertificateAccessTests(TestCase):
    def setUp(self):
        self.hr_role, _ = Roles.objects.get_or_create(role_name="HR")
        self.emp_role, _ = Roles.objects.get_or_create(role_name="Employee")

        self.hr_user = User.objects.create_user(username="hr_cert", password="pass")
        self.owner = User.objects.create_user(username="emp_cert", password="pass")
        self.other = User.objects.create_user(username="other_cert", password="pass")

        Profile.objects.create(
            Employee_id=self.hr_user,
            Role=self.hr_role,
            Name="HR Cert",
            Email_id="hr_cert@test.com",
        )
        Profile.objects.create(
            Employee_id=self.owner,
            Role=self.emp_role,
            Name="Owner Cert",
            Email_id="owner_cert@test.com",
        )
        Profile.objects.create(
            Employee_id=self.other,
            Role=self.emp_role,
            Name="Other Cert",
            Email_id="other_cert@test.com",
        )

        self.cert = EmployeeCertificate.objects.create(
            employee=self.owner,
            uploaded_by=self.owner,
            title="Test Cert",
            description="Sample",
            s3_key="Certificate/test.pdf",
            file_name="test.pdf",
        )
        self.client = APIClient()

    def test_owner_sees_own_certificate(self):
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/certificates/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["employeeId"], "emp_cert")

    def test_other_employee_cannot_see_foreign_certificate(self):
        self.client.force_authenticate(self.other)
        r = self.client.get("/api/certificates/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 0)

    def test_hr_sees_all_active(self):
        self.client.force_authenticate(self.hr_user)
        r = self.client.get("/api/certificates/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)

    def test_employee_cannot_delete_certificate(self):
        self.client.force_authenticate(self.owner)
        r = self.client.delete(f"/api/certificates/{self.cert.pk}/")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(EmployeeCertificate.objects.filter(pk=self.cert.pk).exists())

    def test_hr_hard_delete_removes_row(self):
        self.client.force_authenticate(self.hr_user)
        r = self.client.delete(f"/api/certificates/{self.cert.pk}/")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(EmployeeCertificate.objects.filter(pk=self.cert.pk).exists())

    def test_hr_can_delete_inactive_certificate(self):
        self.cert.is_active = False
        self.cert.save(update_fields=["is_active"])
        self.client.force_authenticate(self.hr_user)
        r = self.client.delete(f"/api/certificates/{self.cert.pk}/")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(EmployeeCertificate.objects.filter(pk=self.cert.pk).exists())

    def test_admin_can_hard_delete(self):
        admin_role, _ = Roles.objects.get_or_create(role_name="Admin")
        admin_user = User.objects.create_user(username="admin_cert", password="pass")
        Profile.objects.create(
            Employee_id=admin_user,
            Role=admin_role,
            Name="Admin Cert",
            Email_id="admin_cert@test.com",
        )
        self.client.force_authenticate(admin_user)
        r = self.client.delete(f"/api/certificates/{self.cert.pk}/")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(EmployeeCertificate.objects.filter(pk=self.cert.pk).exists())

    @patch("certificates.services.upload_certificate_file", return_value="Certificate/mock.pdf")
    def test_batch_upload_multiple(self, _mock_upload):
        self.client.force_authenticate(self.owner)
        f1 = SimpleUploadedFile("a.pdf", b"pdf1", content_type="application/pdf")
        f2 = SimpleUploadedFile("b.pdf", b"pdf2", content_type="application/pdf")
        r = self.client.post(
            "/api/certificates/batch/",
            data={
                "file": [f1, f2],
                "title": ["Cert A", "Cert B"],
                "description": ["Desc A", "Desc B"],
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["created"], 2)
        self.assertEqual(r.data["id"], "emp_cert")
        self.assertEqual(len(r.data["certificate"]), 2)
        self.assertEqual(EmployeeCertificate.objects.filter(employee=self.owner).count(), 3)

    @patch("certificates.grouped.certificate_file_url", return_value="https://example.com/cert.pdf")
    def test_me_grouped_shape(self, _mock_url):
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/certificates/me/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], "emp_cert")
        self.assertIn("name", r.data)
        self.assertIn("certificate", r.data)
        self.assertEqual(len(r.data["certificate"]), 1)
        item = r.data["certificate"][0]
        self.assertIn("title", item)
        self.assertIn("desc", item)
        self.assertIn("link", item)

    @patch("certificates.grouped.certificate_file_url", return_value="https://example.com/cert.pdf")
    def test_grouped_by_employee_id(self, _mock_url):
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/certificates/grouped/?id=emp_cert")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], "emp_cert")
        self.assertEqual(len(r.data["certificate"]), 1)

    @patch("certificates.grouped.certificate_file_url", return_value="https://example.com/cert.pdf")
    def test_grouped_forbidden_other_employee(self, _mock_url):
        self.client.force_authenticate(self.other)
        r = self.client.get("/api/certificates/grouped/?id=emp_cert")
        self.assertEqual(r.status_code, 403)


class CertificationScoringTests(TestCase):
    def setUp(self):
        from django.utils import timezone
        from datetime import datetime

        self.timezone = timezone
        self.datetime = datetime
        self.emp_role, _ = Roles.objects.get_or_create(role_name="Employee")
        self.owner = User.objects.create_user(username="score_cert", password="pass")
        Profile.objects.create(
            Employee_id=self.owner,
            Role=self.emp_role,
            Name="Score Cert",
            Email_id="score_cert@test.com",
        )

    def _create_cert(self, title, year, month, day=5):
        cert = EmployeeCertificate.objects.create(
            employee=self.owner,
            uploaded_by=self.owner,
            title=title,
            s3_key=f"Certificate/{title}.pdf",
            file_name=f"{title}.pdf",
        )
        aware = self.timezone.make_aware(self.datetime(year, month, day, 12, 0, 0))
        EmployeeCertificate.objects.filter(pk=cert.pk).update(created_at=aware)
        cert.refresh_from_db()
        return cert

    def test_one_cert_gives_main_score_only(self):
        from certificates.certification_scoring import build_certification_points

        self._create_cert("AWS", 2026, 6)
        result = build_certification_points(self.owner, 2026, month=6)

        self.assertEqual(result["main_score"], 5.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 5.0)
        self.assertEqual(result["counts"]["certificates"], 1)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["points_type"], "main")

    def test_multiple_certs_split_main_and_bonus(self):
        from certificates.certification_scoring import build_certification_points

        self._create_cert("AWS", 2026, 6, day=5)
        self._create_cert("Azure", 2026, 6, day=10)
        self._create_cert("GCP", 2026, 6, day=15)
        result = build_certification_points(self.owner, 2026, month=6)

        self.assertEqual(result["main_score"], 5.0)
        self.assertEqual(result["monthly_bonus"], 10.0)
        self.assertEqual(result["total_points"], 15.0)
        self.assertEqual(result["counts"]["certificates"], 3)
        self.assertEqual(result["events"][0]["points_type"], "main")
        self.assertEqual(result["events"][1]["points_type"], "bonus")
        self.assertEqual(result["events"][2]["points_type"], "bonus")

    def test_inactive_cert_not_counted(self):
        from certificates.certification_scoring import build_certification_points

        cert = self._create_cert("Old", 2026, 6)
        cert.is_active = False
        cert.save(update_fields=["is_active"])
        result = build_certification_points(self.owner, 2026, month=6)

        self.assertEqual(result["total_points"], 0.0)
        self.assertEqual(result["counts"]["certificates"], 0)

    def test_certification_points_endpoint(self):
        self._create_cert("AWS", 2026, 6)
        self._create_cert("Azure", 2026, 6, day=8)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/certificates/certification-points/?year=2026&month=6")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["main_score"], 5.0)
        self.assertEqual(r.data["monthly_bonus"], 5.0)
        self.assertEqual(r.data["total_points"], 10.0)
