from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import Profile, Roles
from announcements_app.models import AnnouncementPost

User = get_user_model()


class AnnouncementPostListTests(APITestCase):
    def setUp(self):
        self.role = Roles.objects.create(role_name="Employee")
        self.user = User.objects.create_user(username="ANNUSR", password="pass123")
        Profile.objects.create(
            Employee_id=self.user,
            Role=self.role,
            Name="Ann User",
            Email_id="ann@example.com",
        )
        self.client.force_authenticate(user=self.user)
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)

        AnnouncementPost.objects.create(
            title="Today post",
            description="Visible today",
            announcement_date=self.today,
            created_by=self.user,
        )
        AnnouncementPost.objects.create(
            title="Yesterday post",
            description="Hidden on default list",
            announcement_date=self.yesterday,
            created_by=self.user,
        )

    def test_list_returns_only_today_announcements(self):
        response = self.client.get("/api/announcements/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Today post")

    def test_list_date_param_returns_requested_day(self):
        response = self.client.get(
            "/api/announcements/",
            {"date": self.yesterday.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Yesterday post")

    def test_list_pagination_wraps_items(self):
        for i in range(3):
            AnnouncementPost.objects.create(
                title=f"Extra {i}",
                description="Today",
                announcement_date=self.today,
                created_by=self.user,
            )

        response = self.client.get("/api/announcements/", {"limit": "2", "offset": "0"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("items", response.data)
        self.assertIn("pagination", response.data)
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(response.data["pagination"]["total"], 4)
        self.assertTrue(response.data["pagination"]["has_next"])

    def test_retrieve_still_accesses_older_post(self):
        old = AnnouncementPost.objects.get(title="Yesterday post")
        response = self.client.get(f"/api/announcements/{old.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Yesterday post")
