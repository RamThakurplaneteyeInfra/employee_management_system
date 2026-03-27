from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Note


class NotesAPITests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

        self.client = APIClient()
        self.client.force_authenticate(self.user1)

    def test_multi_create_and_list_only_my_notes(self):
        resp = self.client.post(
            "/notesapi/notes/",
            {
                "notes": [
                    {"title": "Work", "content": "Finish report"},
                    {"content": "Call client at 5 PM"},
                ]
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

        # user1 has 2 active notes
        self.assertEqual(Note.objects.filter(created_by=self.user1, is_deleted=False).count(), 2)

        # user2 has one note, user1 must not see it
        Note.objects.create(content="secret", created_by=self.user2)

        resp_list = self.client.get("/notesapi/notes/", format="json")
        self.assertEqual(resp_list.status_code, 200)
        data = resp_list.json()
        ids = [n["id"] for n in data]
        my_ids = list(Note.objects.filter(created_by=self.user1, is_deleted=False).values_list("id", flat=True))
        self.assertCountEqual(ids, my_ids)

    def test_delete_is_soft_delete(self):
        note = Note.objects.create(content="to delete", created_by=self.user1)
        resp = self.client.delete(f"/notesapi/notes/{note.id}/")
        self.assertEqual(resp.status_code, 204)

        note.refresh_from_db()
        self.assertTrue(note.is_deleted)

    def test_user_cannot_retrieve_other_users_note(self):
        other_note = Note.objects.create(content="not yours", created_by=self.user2)
        resp = self.client.get(f"/notesapi/notes/{other_note.id}/")
        self.assertIn(resp.status_code, [404, 403])

