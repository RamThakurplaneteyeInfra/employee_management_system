from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import DeadlineProject, DeadlineProjectPhase


class DeadlineProjectAPITests(TestCase):
    """End-to-end tests for the Project Deadline API."""

    def setUp(self):
        self.admin = User.objects.create_user("admin", password="pass")
        self.admin.is_superuser = True
        self.admin.save()

        self.member = User.objects.create_user("member", password="pass")
        self.other = User.objects.create_user("other", password="pass")

        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _sample_payload(self):
        return {
            "title": "AI Crop Monitoring",
            "branch": "Agriculture",
            "description": "Satellite + AI based crop health system",
            "status": "ACTIVE",
            "deadline": "2026-06-15",
            "phases": [
                {
                    "title": "Phase 1",
                    "date": "2026-02-10",
                    "phase_status": "COMPLETED",
                    "team_lead_id": self.member.id,
                    "member_ids": [self.admin.id],
                    "checklist": [
                        {"text": "Design", "checked": True, "checkedDate": "2026-02-01", "employeeIds": [101, 102]},
                        {"text": "Prototype", "checked": False},
                    ],
                    "notes": "Initial phase",
                },
                {
                    "title": "Phase 2",
                    "date": None,
                    "phase_status": "PENDING",
                    "team_lead_id": None,
                    "member_ids": [],
                    "checklist": [],
                    "notes": "",
                },
            ],
        }

    # ---- CREATE -----------------------------------------------------------

    def test_create_project(self):
        resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["title"], "AI Crop Monitoring")
        self.assertEqual(data["data"]["deadline"], "2026-06-15")
        self.assertIsInstance(data["data"]["id"], int)
        self.assertEqual(len(data["data"]["phases"]), 2)
        phase = data["data"]["phases"][0]
        self.assertIn("checklist", phase)
        self.assertEqual(phase["checklist"], [
            {"text": "Design", "checked": True, "checkedDate": "2026-02-01", "employeeIds": [101, 102], "note": ""},
            {"text": "Prototype", "checked": False, "checkedDate": None, "employeeIds": [], "note": ""},
        ])

    def test_create_project_with_null_deadline(self):
        payload = self._sample_payload()
        payload["deadline"] = None
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.json()["data"]["deadline"])

    def test_create_invalid_status_returns_400(self):
        payload = self._sample_payload()
        payload["status"] = "INVALID"
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["success"])

    def test_create_invalid_checklist_string_returns_400(self):
        payload = self._sample_payload()
        payload["phases"][0]["checklist"] = ["plain string"]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_create_invalid_checklist_missing_checked_returns_400(self):
        payload = self._sample_payload()
        payload["phases"][0]["checklist"] = [{"text": "no checked key"}]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_create_invalid_employee_ids_type_returns_400(self):
        payload = self._sample_payload()
        payload["phases"][0]["checklist"] = [
            {"text": "bad ids", "checked": True, "checkedDate": "2026-02-01", "employeeIds": "101,102"}
        ]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_create_invalid_employee_ids_item_returns_400(self):
        payload = self._sample_payload()
        payload["phases"][0]["checklist"] = [
            {"text": "bad ids", "checked": True, "checkedDate": "2026-02-01", "employeeIds": [101, "bad"]}
        ]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_checklist_defaults_employee_ids_to_empty(self):
        payload = self._sample_payload()
        payload["phases"][0]["checklist"] = [
            {"text": "missing employeeIds", "checked": True, "checkedDate": "2026-02-01"}
        ]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        checklist_item = resp.json()["data"]["phases"][0]["checklist"][0]
        self.assertEqual(checklist_item["employeeIds"], [])
        self.assertEqual(checklist_item["note"], "")

    def test_checklist_note_optional_and_persisted(self):
        payload = self._sample_payload()
        payload["phases"][0]["checklist"] = [
            {"text": "With note", "checked": False, "note": "Blocker: waiting on review"},
            {"text": "No note key", "checked": True, "checkedDate": "2026-02-01"},
        ]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        ch = resp.json()["data"]["phases"][0]["checklist"]
        self.assertEqual(ch[0]["note"], "Blocker: waiting on review")
        self.assertEqual(ch[1]["note"], "")

    def test_checklist_invalid_note_type_returns_400(self):
        payload = self._sample_payload()
        payload["phases"][0]["checklist"] = [
            {"text": "bad note", "checked": False, "note": 99},
        ]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    # ---- LIST -------------------------------------------------------------

    def test_list_projects(self):
        self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        resp = self.client.get("/deadline/projects/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        self.assertEqual(len(resp.json()["data"]), 1)

    def test_list_filter_by_status(self):
        self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        resp = self.client.get("/deadline/projects/?status=ACTIVE")
        self.assertEqual(len(resp.json()["data"]), 1)
        resp = self.client.get("/deadline/projects/?status=COMPLETED")
        self.assertEqual(len(resp.json()["data"]), 0)

    def test_list_search(self):
        self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        resp = self.client.get("/deadline/projects/?search=Crop")
        self.assertEqual(len(resp.json()["data"]), 1)
        resp = self.client.get("/deadline/projects/?search=zzzzz")
        self.assertEqual(len(resp.json()["data"]), 0)

    # ---- DETAIL -----------------------------------------------------------

    def test_get_detail(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        resp = self.client.get(f"/deadline/projects/{pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        self.assertEqual(resp.json()["data"]["id"], pk)

    def test_get_not_found(self):
        resp = self.client.get("/deadline/projects/999999/")
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(resp.json()["success"])

    # ---- PATCH ------------------------------------------------------------

    def test_patch_update_deadline(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        resp = self.client.patch(f"/deadline/projects/{pk}/", {"deadline": "2026-12-31"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["deadline"], "2026-12-31")

    def test_patch_set_deadline_null(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        resp = self.client.patch(f"/deadline/projects/{pk}/", {"deadline": None}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["data"]["deadline"])

    def test_patch_replace_phases(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        new_phases = [{
            "title": "Single Phase",
            "phase_status": "IN_PROGRESS",
            "team_lead_id": self.member.id,
            "member_ids": [self.admin.id],
            "checklist": [
                {"text": "a", "checked": False},
                {"text": "b", "checked": True},
            ],
        }]
        resp = self.client.patch(f"/deadline/projects/{pk}/", {"phases": new_phases}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["data"]["phases"]), 1)
        self.assertEqual(resp.json()["data"]["phases"][0]["checklist"], [
            {"text": "a", "checked": False, "checkedDate": None, "employeeIds": [], "note": ""},
            {"text": "b", "checked": True, "checkedDate": None, "employeeIds": [], "note": ""},
        ])
        total = DeadlineProjectPhase.objects.filter(project_id=pk).count()
        archived = DeadlineProjectPhase.objects.filter(project_id=pk, archived=True).count()
        self.assertEqual(archived, 2)
        self.assertEqual(total, 3)

    # ---- SOFT DELETE ------------------------------------------------------

    def test_delete_is_soft(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        resp = self.client.delete(f"/deadline/projects/{pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        self.assertTrue(DeadlineProject.objects.filter(pk=pk).exists())
        self.assertTrue(DeadlineProject.objects.get(pk=pk).archived)

    def test_deleted_project_hidden_from_list(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        self.client.delete(f"/deadline/projects/{pk}/")
        resp = self.client.get("/deadline/projects/")
        self.assertEqual(len(resp.json()["data"]), 0)

    # ---- NO 403 RULE ------------------------------------------------------

    def test_unauthorized_write_returns_200_not_403(self):
        """A normal member (not MD/Admin/creator) should get 200 success:false, never 403."""
        self.client.force_authenticate(self.other)
        resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["success"])
        self.assertIn("not authorized", resp.json()["message"].lower())

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(None)
        resp = self.client.get("/deadline/projects/")
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.json()["success"])

    # ---- PHASE TEAM LEAD + MEMBERS (unchanged) ----------------------------

    def test_phase_team_lead_and_members(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        phase = create_resp.json()["data"]["phases"][0]
        self.assertEqual(phase["teamLeadId"], self.member.id)
        self.assertEqual(phase["memberIds"], [self.admin.id])

    # ---- INTEGER IDS ------------------------------------------------------

    def test_ids_are_integers(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        data = create_resp.json()["data"]
        self.assertIsInstance(data["id"], int)
        self.assertIsInstance(data["createdBy"], int)
        for phase in data["phases"]:
            self.assertIsInstance(phase["id"], int)

    # ---- ACCEPTS ANY USER ID (no FK constraint) ---------------------------

    def test_phase_accepts_any_team_lead_id(self):
        """team_lead_id can be any integer — no auth_user FK check."""
        payload = self._sample_payload()
        payload["phases"] = [{
            "title": "Phase X",
            "phase_status": "PENDING",
            "team_lead_id": 99999,
            "member_ids": [88888, 77777],
            "checklist": [],
            "notes": "",
        }]
        resp = self.client.post("/deadline/projects/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        phase = resp.json()["data"]["phases"][0]
        self.assertEqual(phase["teamLeadId"], 99999)
        self.assertEqual(phase["memberIds"], [88888, 77777])

    # ---- ACCESS CONTROL (list / detail / phases / PATCH) -------------------

    def test_superuser_sees_all_phases_on_list_and_detail(self):
        self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        resp = self.client.get("/deadline/projects/")
        self.assertEqual(len(resp.json()["data"]), 1)
        self.assertEqual(len(resp.json()["data"][0]["phases"]), 2)
        pk = resp.json()["data"][0]["id"]
        detail = self.client.get(f"/deadline/projects/{pk}/")
        self.assertEqual(len(detail.json()["data"]["phases"]), 2)

    def test_creator_sees_all_phases_and_can_patch(self):
        creator = User.objects.create_user("creator", password="pass")
        project = DeadlineProject.objects.create(
            title="Creator Project",
            branch="",
            description="",
            status="ACTIVE",
            created_by=creator,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="Phase A",
            phase_status="PENDING",
            team_lead_id=99999,
            member_ids=[],
            checklist=[],
            notes="",
            sort_order=0,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="Phase B",
            phase_status="PENDING",
            team_lead_id=None,
            member_ids=[],
            checklist=[],
            notes="",
            sort_order=1,
        )
        self.client.force_authenticate(creator)
        resp = self.client.get(f"/deadline/projects/{project.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["data"]["phases"]), 2)
        r2 = self.client.patch(
            f"/deadline/projects/{project.pk}/",
            {"title": "Updated by creator"},
            format="json",
        )
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()["success"])
        self.assertEqual(r2.json()["data"]["title"], "Updated by creator")

    def test_phase_only_member_sees_assigned_phases_only_cannot_patch(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        self.client.force_authenticate(self.member)
        list_resp = self.client.get("/deadline/projects/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.json()["data"]), 1)
        self.assertEqual(
            len(list_resp.json()["data"][0]["phases"]),
            1,
            "member is team lead only on first phase",
        )
        detail_resp = self.client.get(f"/deadline/projects/{pk}/")
        self.assertEqual(len(detail_resp.json()["data"]["phases"]), 1)
        patch_resp = self.client.patch(
            f"/deadline/projects/{pk}/",
            {"title": "Hacked"},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertFalse(patch_resp.json()["success"])

    def test_unrelated_user_empty_list_and_404_detail(self):
        create_resp = self.client.post("/deadline/projects/", self._sample_payload(), format="json")
        pk = create_resp.json()["data"]["id"]
        self.client.force_authenticate(self.other)
        list_resp = self.client.get("/deadline/projects/")
        self.assertEqual(list_resp.json()["data"], [])
        detail_resp = self.client.get(f"/deadline/projects/{pk}/")
        self.assertEqual(detail_resp.status_code, 404)
        self.assertFalse(detail_resp.json()["success"])


class ChecklistScoringTests(TestCase):
    def setUp(self):
        from accounts.models import Profile, Roles

        self.role_employee = Roles.objects.create(role_name="Employee")
        self.role_intern = Roles.objects.create(role_name="Intern")
        self.role_teamlead = Roles.objects.create(role_name="TeamLead")

        self.tl = User.objects.create_user(username="200018", password="pass")
        self.emp = User.objects.create_user(username="300013", password="pass")
        self.intern = User.objects.create_user(username="50016", password="pass")

        Profile.objects.create(
            Employee_id=self.tl,
            Role=self.role_teamlead,
            Name="Team Lead",
            Email_id="tl@example.com",
        )
        Profile.objects.create(
            Employee_id=self.emp,
            Role=self.role_employee,
            Teamlead=self.tl,
            Name="Employee",
            Email_id="emp@example.com",
        )
        Profile.objects.create(
            Employee_id=self.intern,
            Role=self.role_intern,
            Teamlead=self.tl,
            Name="Intern",
            Email_id="intern@example.com",
        )

        project = DeadlineProject.objects.create(
            title="EMS Platform",
            status="ACTIVE",
            created_by=self.tl,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="Discovery",
            team_lead_id=200018,
            checklist=self._checklist_items(),
            sort_order=0,
        )

    def _checklist_items(self):
        items = []
        for idx, emp_id in enumerate([200018, 300013, 50016, 300013], start=1):
            items.append(
                {
                    "text": f"Task {idx}",
                    "checked": True,
                    "checkedDate": "2026-04-15",
                    "employeeIds": [emp_id],
                    "note": "",
                }
            )
        for idx in range(5, 9):
            items.append(
                {
                    "text": f"Employee extra {idx}",
                    "checked": True,
                    "checkedDate": "2026-04-20",
                    "employeeIds": [300013],
                    "note": "",
                }
            )
        return items

    def test_employee_score_monthly_cap(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        result = build_checklist_points(self.emp, 2026, month=4)

        self.assertEqual(result["role_type"], "employee")
        self.assertEqual(result["counts"]["completed_checklists"], 6)
        self.assertEqual(result["max_points"], 70.0)
        self.assertEqual(result["monthly_max_points"], 70.0)
        self.assertEqual(result["main_score"], 70.0)
        self.assertEqual(result["monthly_bonus"], 35.0)
        self.assertEqual(result["total_points"], 105.0)

    def test_team_lead_phase_score_monthly_cap(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        result = build_checklist_points(self.tl, 2026, month=4)

        self.assertEqual(result["role_type"], "team_lead")
        self.assertEqual(result["phase_stats"]["phases_as_team_lead"], 1)
        self.assertEqual(result["completed_by"]["team_lead"], 1)
        self.assertEqual(result["completed_by"]["employees"], 6)
        self.assertEqual(result["completed_by"]["interns"], 1)
        self.assertEqual(result["completed_by"]["aggregated_total"], 8)
        self.assertEqual(result["max_points"], 70.0)
        self.assertEqual(result["main_score"], 70.0)
        self.assertEqual(result["monthly_bonus"], 10.0)
        self.assertEqual(result["total_points"], 80.0)

    def test_team_lead_gets_credit_when_member_completes_on_led_phase(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        project = DeadlineProject.objects.create(
            title="EMS",
            status="ACTIVE",
            created_by=self.tl,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="Validation",
            team_lead_id=200018,
            checklist=[
                {
                    "text": "Map user journey",
                    "checked": True,
                    "checkedDate": "2026-06-11",
                    "employeeIds": [300013],
                    "note": "",
                },
            ],
            sort_order=0,
        )

        result = build_checklist_points(self.tl, 2026, month=6)

        self.assertEqual(result["completed_by"]["aggregated_total"], 1)
        self.assertEqual(result["completed_by"]["team_lead"], 0)
        self.assertEqual(result["completed_by"]["employees"], 1)
        self.assertEqual(result["total_points"], 10.0)

    def test_team_lead_no_credit_without_phase_team_lead_id(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        project = DeadlineProject.objects.create(
            title="Other Project",
            status="ACTIVE",
            created_by=self.tl,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="No TL Phase",
            team_lead_id=None,
            checklist=[
                {
                    "text": "Task",
                    "checked": True,
                    "checkedDate": "2026-04-15",
                    "employeeIds": [300013],
                    "note": "",
                },
            ],
            sort_order=0,
        )

        result = build_checklist_points(self.tl, 2026, month=4)

        self.assertEqual(result["completed_by"]["aggregated_total"], 8)

    def test_assigned_team_lead_on_other_team_leads_phase_gets_tl_points(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        other_tl = User.objects.create_user(username="200024", password="pass")
        from accounts.models import Profile

        Profile.objects.create(
            Employee_id=other_tl,
            Role=self.role_teamlead,
            Name="Other Team Lead",
            Email_id="other_tl@example.com",
        )

        project = DeadlineProject.objects.create(
            title="Shared TL Credit",
            status="ACTIVE",
            created_by=self.tl,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="Validation",
            team_lead_id=200024,
            checklist=[
                {
                    "text": "Checklist by another TL",
                    "checked": True,
                    "checkedDate": "2026-06-11",
                    "employeeIds": [200018],
                    "note": "",
                },
            ],
            sort_order=0,
        )

        result_phase_tl = build_checklist_points(other_tl, 2026, month=6)
        result_assigned_tl = build_checklist_points(self.tl, 2026, month=6)

        self.assertEqual(result_phase_tl["completed_by"]["aggregated_total"], 1)
        self.assertEqual(result_phase_tl["total_points"], 10.0)
        self.assertEqual(result_assigned_tl["completed_by"]["assigned_team_lead"], 1)
        self.assertEqual(result_assigned_tl["completed_by"]["aggregated_total"], 1)
        self.assertEqual(result_assigned_tl["total_points"], 10.0)

    def test_same_team_lead_not_double_counted_when_phase_lead_and_assignee(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        project = DeadlineProject.objects.create(
            title="No Double Count",
            status="ACTIVE",
            created_by=self.tl,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="Discovery",
            team_lead_id=200018,
            checklist=[
                {
                    "text": "TL owns and completes",
                    "checked": True,
                    "checkedDate": "2026-06-12",
                    "employeeIds": [200018],
                    "note": "",
                },
            ],
            sort_order=0,
        )

        result = build_checklist_points(self.tl, 2026, month=6)

        self.assertEqual(result["completed_by"]["team_lead"], 1)
        self.assertEqual(result["completed_by"]["assigned_team_lead"], 0)
        self.assertEqual(result["completed_by"]["aggregated_total"], 1)
        self.assertEqual(result["total_points"], 10.0)

    def test_employee_yearly_score_sums_monthly_caps(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        result = build_checklist_points(self.emp, 2026)

        self.assertEqual(result["period_type"], "year")
        self.assertEqual(result["max_points"], 840.0)
        self.assertEqual(result["months_in_period"], 12)
        self.assertEqual(result["counts"]["completed_checklists"], 6)
        self.assertEqual(result["main_score"], 70.0)
        self.assertEqual(result["monthly_bonus"], 35.0)
        self.assertEqual(result["total_points"], 105.0)

    def test_team_lead_bonus_only_when_above_monthly_main_cap(self):
        from projects_deadline.checklist_scoring import build_checklist_points

        project = DeadlineProject.objects.create(
            title="Bonus Check",
            status="ACTIVE",
            created_by=self.tl,
        )
        DeadlineProjectPhase.objects.create(
            project=project,
            title="Bonus Month",
            team_lead_id=200018,
            checklist=[
                {
                    "text": "Single checklist",
                    "checked": True,
                    "checkedDate": "2026-08-01",
                    "employeeIds": [200018],
                    "note": "",
                },
            ],
            sort_order=0,
        )

        result = build_checklist_points(self.tl, 2026, month=8)

        self.assertEqual(result["completed_by"]["aggregated_total"], 1)
        self.assertEqual(result["main_score"], 10.0)
        self.assertEqual(result["monthly_bonus"], 0.0)
        self.assertEqual(result["total_points"], 10.0)
