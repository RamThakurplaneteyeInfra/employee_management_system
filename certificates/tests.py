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

    def test_soft_delete_keeps_row(self):
        self.client.force_authenticate(self.owner)
        r = self.client.delete(f"/api/certificates/{self.cert.pk}/")
        self.assertEqual(r.status_code, 204)
        self.assertTrue(EmployeeCertificate.objects.filter(pk=self.cert.pk).exists())
        self.cert.refresh_from_db()
        self.assertFalse(self.cert.is_active)

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
