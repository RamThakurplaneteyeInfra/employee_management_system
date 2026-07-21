from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import Functions, Profile, Roles
from CustomerPanel.models import CustomerPanelAmountLog, CustomerPanelEntry


class CustomerPanelEntriesScoringTests(TestCase):
    def setUp(self):
        self.role_employee = Roles.objects.create(role_name="Employee")
        self.emp = User.objects.create_user(username="mmr_user", password="pass")
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Name="MMR Employee",
            Email_id="mmr@test.com",
        )
        self.mmr = Functions.objects.create(function="MMR")
        self.rg = Functions.objects.create(function="RG")

    def _aware_june(self, day: int) -> datetime:
        return timezone.make_aware(datetime(2026, 6, day, 10, 0, 0))

    def _create_entry(self, total: Decimal, day: int = 5, log_creator=None):
        """Create an entry plus one amount log; scoring is driven by the log."""
        entry = CustomerPanelEntry.objects.create(
            business_name=f"Biz {day}",
            division=CustomerPanelEntry.DIVISION_FARM,
            total=total,
            created_by=self.emp,
        )
        CustomerPanelEntry.objects.filter(pk=entry.pk).update(created_at=self._aware_june(day))
        CustomerPanelAmountLog.objects.create(
            entry=entry,
            amount=total,
            date=date(2026, 6, day),
            created_by=log_creator or self.emp,
        )
        return entry

    def test_not_eligible_without_mmr_or_rg(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points

        self._create_entry(Decimal("500000"))
        result = build_customer_panel_entries_points(self.emp, 2026, month=6)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["total_points"], 0.0)

    def test_five_lakh_hits_main_cap(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points

        profile = Profile.objects.get(Employee_id=self.emp)
        profile.functions.add(self.mmr)
        self._create_entry(Decimal("500000"))
        result = build_customer_panel_entries_points(self.emp, 2026, month=6)

        self.assertTrue(result["eligible"])
        self.assertEqual(result["main_score"], 40.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 40.0)
        self.assertEqual(result["counts"]["total_amount"], 500000.0)

    def test_six_lakh_adds_bonus(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points

        profile = Profile.objects.get(Employee_id=self.emp)
        profile.functions.add(self.rg)
        self._create_entry(Decimal("600000"))
        result = build_customer_panel_entries_points(self.emp, 2026, month=6)

        self.assertEqual(result["main_score"], 40.0)
        self.assertEqual(result["monthly_bonus"], 8.0)
        self.assertEqual(result["total_points"], 48.0)

    def test_two_fifty_thousand_is_twenty_points(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points

        profile = Profile.objects.get(Employee_id=self.emp)
        profile.functions.add(self.mmr)
        self._create_entry(Decimal("250000"))
        result = build_customer_panel_entries_points(self.emp, 2026, month=6)

        self.assertEqual(result["main_score"], 20.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 20.0)

    def test_points_go_to_log_creator_not_entry_creator(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points

        profile = Profile.objects.get(Employee_id=self.emp)
        profile.functions.add(self.mmr)

        other = User.objects.create_user(username="entry_owner", password="pass")
        Profile.objects.create(
            Employee_id=other,
            Role=self.role_employee,
            Name="Entry Owner",
            Email_id="owner@test.com",
        )
        entry = CustomerPanelEntry.objects.create(
            business_name="Owned by other",
            division=CustomerPanelEntry.DIVISION_FARM,
            total=Decimal("500000"),
            created_by=other,
        )
        CustomerPanelAmountLog.objects.create(
            entry=entry,
            amount=Decimal("500000"),
            date=date(2026, 6, 10),
            created_by=self.emp,
        )

        result = build_customer_panel_entries_points(self.emp, 2026, month=6)
        self.assertEqual(result["main_score"], 40.0)

        other_result = build_customer_panel_entries_points(other, 2026, month=6)
        self.assertEqual(other_result["total_points"], 0.0)

    def test_log_date_decides_scoring_month(self):
        from CustomerPanel.customer_panel_scoring import build_customer_panel_entries_points

        profile = Profile.objects.get(Employee_id=self.emp)
        profile.functions.add(self.mmr)

        entry = CustomerPanelEntry.objects.create(
            business_name="Backdated",
            division=CustomerPanelEntry.DIVISION_FARM,
            total=Decimal("500000"),
            created_by=self.emp,
        )
        # Log entered now, but dated in May: points must land in May, not June.
        CustomerPanelAmountLog.objects.create(
            entry=entry,
            amount=Decimal("500000"),
            date=date(2026, 5, 20),
            created_by=self.emp,
        )

        june = build_customer_panel_entries_points(self.emp, 2026, month=6)
        self.assertEqual(june["total_points"], 0.0)

        may = build_customer_panel_entries_points(self.emp, 2026, month=5)
        self.assertEqual(may["main_score"], 40.0)

    def test_points_endpoint(self):
        profile = Profile.objects.get(Employee_id=self.emp)
        profile.functions.add(self.mmr)
        self._create_entry(Decimal("125000"))
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(self.emp)
        response = client.get("/customerpanelapi/entries/points/?year=2026&month=6")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["eligible"])
        self.assertEqual(response.data["total_points"], 10.0)
