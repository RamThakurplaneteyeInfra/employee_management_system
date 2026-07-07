from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Profile, Roles
from events.meeting_scoring import build_meeting_points
from events.models import BookSlot, BookingStatus, Room, SlotMembers


class MeetingScoringTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.confirmed = BookingStatus.objects.create(status_name="Confirmed")
        self.cancelled = BookingStatus.objects.create(status_name="Cancelled")
        self.indoor_room = Room.objects.create(name="Conference A")
        self.outdoor_room = Room.objects.create(name="Outdoor")
        self.emp = User.objects.create_user(username="EMP200", password="pass123")
        self.other = User.objects.create_user(username="EMP201", password="pass123")
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="Meeting Employee",
            Email_id="meet@example.com",
        )

    def _create_slot(self, *, room, slot_date, creator=None, members=None):
        slot = BookSlot.objects.create(
            meeting_title="Test meeting",
            date=slot_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            room=room,
            meeting_type="group",
            status=self.confirmed,
            created_by=creator or self.emp,
        )
        for member in members or [self.emp]:
            SlotMembers.objects.create(slot=slot, member=member)
        return slot

    def test_indoor_and_outdoor_points(self):
        self._create_slot(room=self.indoor_room, slot_date=date(2026, 6, 5))
        self._create_slot(room=self.indoor_room, slot_date=date(2026, 6, 8))
        self._create_slot(room=self.outdoor_room, slot_date=date(2026, 6, 12))

        result = build_meeting_points(self.emp, 2026, month=6)

        self.assertEqual(result["counts"]["indoor_meetings"], 2)
        self.assertEqual(result["counts"]["outdoor_meetings"], 1)
        self.assertEqual(result["counts"]["total_meetings"], 3)
        self.assertEqual(result["points"]["indoor_gross"], 0.5)
        self.assertEqual(result["points"]["outdoor_gross"], 0.5)
        self.assertEqual(result["points"]["indoor"], 0.5)
        self.assertEqual(result["points"]["outdoor"], 0.5)
        self.assertEqual(result["points"]["indoor_bonus"], 0.0)
        self.assertEqual(result["points"]["outdoor_bonus"], 0.0)
        self.assertEqual(result["points"]["raw_total"], 1.0)
        self.assertEqual(result["main_score"], 1.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 1.0)
        self.assertEqual(result["max_main_points"], 7.0)
        self.assertEqual(result["max_indoor_points"], 3.5)

    def test_indoor_cap_at_three_point_five_per_month(self):
        for day in range(1, 29):
            self._create_slot(room=self.indoor_room, slot_date=date(2026, 6, day))

        result = build_meeting_points(self.emp, 2026, month=6)

        self.assertEqual(result["counts"]["indoor_meetings"], 28)
        self.assertEqual(result["points"]["indoor_gross"], 7.0)
        self.assertEqual(result["points"]["indoor"], 3.5)
        self.assertEqual(result["points"]["indoor_bonus"], 3.5)
        self.assertEqual(result["main_score"], 3.5)
        self.assertEqual(result["monthly_bonus"], 3.5)
        self.assertEqual(result["total_points"], 7.0)

    def test_separate_indoor_and_outdoor_caps(self):
        for day in range(1, 15):
            self._create_slot(room=self.indoor_room, slot_date=date(2026, 6, day))
        for day in range(15, 22):
            self._create_slot(room=self.outdoor_room, slot_date=date(2026, 6, day))

        result = build_meeting_points(self.emp, 2026, month=6)

        self.assertEqual(result["points"]["indoor_gross"], 3.5)
        self.assertEqual(result["points"]["outdoor_gross"], 3.5)
        self.assertEqual(result["points"]["indoor"], 3.5)
        self.assertEqual(result["points"]["outdoor"], 3.5)
        self.assertEqual(result["points"]["indoor_bonus"], 0.0)
        self.assertEqual(result["points"]["outdoor_bonus"], 0.0)
        self.assertEqual(result["main_score"], 7.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 7.0)

    def test_cancelled_meetings_excluded(self):
        slot = self._create_slot(room=self.indoor_room, slot_date=date(2026, 6, 5))
        slot.status = self.cancelled
        slot.save(update_fields=["status"])

        result = build_meeting_points(self.emp, 2026, month=6)
        self.assertEqual(result["counts"]["total_meetings"], 0)
        self.assertEqual(result["main_score"], 0.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 0.0)

    def test_creator_without_member_row_still_counts(self):
        slot = BookSlot.objects.create(
            meeting_title="Creator only",
            date=date(2026, 6, 9),
            start_time=time(9, 0),
            end_time=time(10, 0),
            room=self.outdoor_room,
            meeting_type="individual",
            status=self.confirmed,
            created_by=self.emp,
        )
        SlotMembers.objects.create(slot=slot, member=self.other)

        result = build_meeting_points(self.emp, 2026, month=6)
        self.assertEqual(result["counts"]["outdoor_meetings"], 1)
        self.assertEqual(result["main_score"], 0.5)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 0.5)


class BookSlotOutdoorOverlapTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.confirmed = BookingStatus.objects.create(status_name="Confirmed")
        self.indoor_room = Room.objects.create(name="Conference A")
        self.outdoor_room = Room.objects.create(name="Outdoor")
        self.emp = User.objects.create_user(username="EMP200", password="pass123")
        self.other = User.objects.create_user(username="EMP201", password="pass123")
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="Meeting Employee",
            Email_id="meet@example.com",
        )
        Profile.objects.create(
            Employee_id=self.other,
            Role=self.role_employee,
            Name="Other Employee",
            Email_id="other@example.com",
        )
        self.slot_date = date(2026, 7, 1)
        self.start = time(10, 0)
        self.end = time(17, 0)

    def _outdoor_payload(self, *, username="EMP201", member_name=None):
        return {
            "meeting_title": "Outdoor meeting",
            "date": self.slot_date.isoformat(),
            "start_time": self.start.isoformat(),
            "end_time": self.end.isoformat(),
            "room": "Outdoor",
            "meeting_type": "group",
            "status": "Confirmed",
            "members": [username],
            "member_name": member_name or ["Field Team"],
        }

    def _validate(self, user, data):
        from rest_framework.test import APIRequestFactory

        from events.serializers import BookSlotSerializer

        request = APIRequestFactory().post("/eventsapi/bookslots/")
        request.user = user
        serializer = BookSlotSerializer(data=data, context={"request": request})
        return serializer

    def test_multiple_outdoor_same_time_allowed_for_different_creators(self):
        slot = BookSlot.objects.create(
            meeting_title="Outdoor 1",
            date=self.slot_date,
            start_time=self.start,
            end_time=self.end,
            room=self.outdoor_room,
            meeting_type="group",
            status=self.confirmed,
            created_by=self.emp,
            member_name=["Team A"],
        )
        SlotMembers.objects.create(slot=slot, member=self.emp)

        serializer = self._validate(self.other, self._outdoor_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_indoor_double_book_still_blocked(self):
        slot = BookSlot.objects.create(
            meeting_title="Indoor 1",
            date=self.slot_date,
            start_time=self.start,
            end_time=self.end,
            room=self.indoor_room,
            meeting_type="group",
            status=self.confirmed,
            created_by=self.emp,
        )
        SlotMembers.objects.create(slot=slot, member=self.emp)

        serializer = self._validate(
            self.other,
            {
                "meeting_title": "Indoor 2",
                "date": self.slot_date.isoformat(),
                "start_time": self.start.isoformat(),
                "end_time": self.end.isoformat(),
                "room": "Conference A",
                "meeting_type": "group",
                "status": "Confirmed",
                "members": ["EMP201"],
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("already booked", str(serializer.errors).lower())
