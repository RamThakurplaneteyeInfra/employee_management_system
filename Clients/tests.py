from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import Functions, Profile, Roles
from Clients.models import ClientProfile, CurrentClientStage


class ClientProfileScoringTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.emp = User.objects.create_user(username="mmr_client", password="pass")
        profile = Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="MMR Client Scorer",
            Email_id="mmrclient@test.com",
        )
        self.mmr = Functions.objects.create(function="MMR")
        profile.functions.add(self.mmr)
        self.proposal, _ = CurrentClientStage.objects.get_or_create(name="Proposal")
        self.proforma, _ = CurrentClientStage.objects.get_or_create(name="Proforma")
        self.leads, _ = CurrentClientStage.objects.get_or_create(name="Leads")

    def _aware_june(self, day: int) -> datetime:
        return timezone.make_aware(datetime(2026, 6, day, 10, 0, 0))

    def _create_profile(self, *, stage, value: Decimal | None, day: int = 5):
        profile = ClientProfile.objects.create(
            company_name=f"Co {day}",
            client_name=f"Client {day}",
            status=stage,
            product_value=value,
            created_by=self.emp,
        )
        ClientProfile.objects.filter(pk=profile.pk).update(created_at=self._aware_june(day))
        return profile

    def test_not_eligible_without_mmr_or_rg(self):
        from Clients.client_profile_scoring import build_client_profile_points

        other = User.objects.create_user(username="other", password="pass")
        Profile.objects.create(
            Employee_id=other,
            Role=self.role_employee,
            Name="Other",
            Email_id="other@test.com",
        )
        self._create_profile(stage=self.proposal, value=Decimal("5000000"), day=5)
        result = build_client_profile_points(other, 2026, month=6)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["total_points"], 0.0)

    def test_five_profiles_scores_ten_on_count_component(self):
        from Clients.client_profile_scoring import build_client_profile_points

        for day in range(1, 6):
            self._create_profile(stage=self.leads, value=None, day=day)

        result = build_client_profile_points(self.emp, 2026, month=6)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["components"]["profile_count"]["main_score"], 10.0)
        self.assertEqual(result["components"]["profile_count"]["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 10.0)

    def test_proposal_fifty_lakh_scores_ten(self):
        from Clients.client_profile_scoring import build_client_profile_points

        self._create_profile(stage=self.proposal, value=Decimal("5000000"), day=10)
        result = build_client_profile_points(self.emp, 2026, month=6)

        self.assertEqual(result["components"]["proposal_value"]["main_score"], 10.0)
        self.assertEqual(result["components"]["proposal_value"]["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 10.0)

    def test_proforma_eleven_lakh_scores_ten(self):
        from Clients.client_profile_scoring import build_client_profile_points

        self._create_profile(stage=self.proforma, value=Decimal("1100000"), day=12)
        result = build_client_profile_points(self.emp, 2026, month=6)

        self.assertEqual(result["components"]["proforma_value"]["main_score"], 10.0)
        self.assertEqual(result["total_points"], 10.0)

    def test_six_profiles_adds_count_bonus(self):
        from Clients.client_profile_scoring import build_client_profile_points

        for day in range(1, 7):
            self._create_profile(stage=self.leads, value=None, day=day)

        result = build_client_profile_points(self.emp, 2026, month=6)
        self.assertEqual(result["components"]["profile_count"]["main_score"], 10.0)
        self.assertEqual(result["components"]["profile_count"]["monthly_bonus"], 2.0)
        self.assertEqual(result["total_points"], 12.0)


class ClientProfileReminderCycleTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.emp = User.objects.create_user(username="lead_creator", password="pass")
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="Lead Creator",
            Email_id="lead@test.com",
        )
        self.leads, _ = CurrentClientStage.objects.get_or_create(name="Leads")

    def test_create_defaults_reminder_cycle_to_zero(self):
        profile = ClientProfile.objects.create(
            company_name="Test Co",
            client_name="Test Client",
            status=self.leads,
            created_by=self.emp,
        )
        self.assertEqual(profile.follow_up_reminder_last_cycle, 0)

    def test_ack_increments_reminder_cycle(self):
        from Clients.views import _ack_profile_reminder_sync

        profile = ClientProfile.objects.create(
            company_name="Test Co",
            client_name="Test Client",
            status=self.leads,
            created_by=self.emp,
        )
        _ack_profile_reminder_sync(self.emp, profile.id)
        profile.refresh_from_db()
        self.assertEqual(profile.follow_up_reminder_last_cycle, 1)
        self.assertIsNotNone(profile.last_reminded_at)
