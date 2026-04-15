from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ems.auth_utils import CsrfExemptSessionAuthentication

from .models import ApprovalStatus, JobApplication, JobOpening, JobState
from .permissions import CanManageJobOpenings, CanToggleJobState, user_can_manage_jobs
from .serializers import (
    JobApplySerializer,
    JobOpeningDetailSerializer,
    JobOpeningListSerializer,
    JobOpeningWriteSerializer,
    requirement_accepts_applications,
)

# Max applicants per batch request (abuse guard).
_APPLY_BATCH_MAX = 50


class JobOpeningViewSet(viewsets.ModelViewSet):
    """
    Jobs API.

    - **GET** list/detail: everyone sees only **MD+HR approved** jobs unless the user is MD/HR/Admin/Team lead (then all non-deleted rows).
    - **POST/PATCH/PUT**: MD, HR, Admin, Team lead only (`created_by` set on create).
    - **POST** ``.../jobs/{id}/open/`` and ``.../jobs/{id}/close/``: creator-only (toggles ``job_state``).
    - **DELETE**: same managers only — **soft-delete** (sets ``deleted_at``); **no row is removed** from the database; applications stay linked.
    - **GET** ``.../jobs/apply/``: list all visible jobs for apply flow (no job id required).
    - **GET** ``.../jobs/{id}/apply/`` / ``apply-batch/``: returns JSON **how to submit** (no 405 when opened in a browser).
    - **POST** ``.../jobs/{id}/apply/``: anyone may apply (name + resume); logged-in users get ``applied_by`` set.
    - **POST** ``.../jobs/{id}/apply-batch/``: multipart batch — repeat ``full_name`` and ``resume`` fields (same count, same order); only when MD+HR approved.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [CanManageJobOpenings]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    queryset = JobOpening.objects.all()

    def get_queryset(self):
        qs = (
            JobOpening.objects.filter(deleted_at__isnull=True)
            .select_related("created_by")
            .prefetch_related(
                Prefetch(
                    "applications",
                    queryset=JobApplication.objects.select_related("applied_by").order_by(
                        "-applied_at"
                    ),
                ),
            )
        )
        user = self.request.user
        if user_can_manage_jobs(user):
            return qs
        return qs.filter(
            md_status=ApprovalStatus.APPROVED,
            hr_status=ApprovalStatus.APPROVED,
        )

    def get_serializer_class(self):
        if self.action == "create":
            return JobOpeningWriteSerializer
        if self.action in ("update", "partial_update"):
            return JobOpeningWriteSerializer
        if self.action == "retrieve":
            return JobOpeningDetailSerializer
        return JobOpeningListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.action == "retrieve":
            ctx["include_applicants"] = user_can_manage_jobs(self.request.user)
        return ctx

    def perform_destroy(self, instance):
        """Soft-delete: keep ``JobOpening`` and ``JobApplication`` rows in the database."""
        instance.deleted_at = timezone.now()
        instance.save()

    def perform_update(self, serializer):
        """
        Allow PATCH/PUT for managers as before, but restrict changing ``job_state``
        through write endpoints to the job creator only.
        """
        instance = self.get_object()
        if "job_state" in serializer.validated_data:
            user = getattr(self.request, "user", None)
            if not user or getattr(instance, "created_by_id", None) != getattr(user, "id", None):
                raise PermissionDenied("Only the creator can change job_state.")
        serializer.save()

    @action(
        detail=False,
        methods=["get"],
        url_path="apply",
        permission_classes=[AllowAny],
        authentication_classes=[CsrfExemptSessionAuthentication],
    )
    def apply_all(self, request):
        """
        GET /jobs/apply/:
        Return only jobs that currently accept applications.
        """
        openings = self.get_queryset().filter(
            md_status=ApprovalStatus.APPROVED,
            hr_status=ApprovalStatus.APPROVED,
            job_state=JobState.OPEN,
        ).order_by("-created_at")
        payload = []
        for opening in openings:
            payload.append(
                {
                    "id": opening.pk,
                    "title": opening.title,
                    "department": opening.department,
                    "team": opening.team,
                    "type": opening.employment_type,
                    "num_positions": opening.num_positions,
                    "required_experience": opening.required_experience,
                    "primary_skills": opening.primary_skills,
                    "education": opening.education,
                    "tools_tech": opening.tools_tech,
                    "md_status": opening.md_status,
                    "hr_status": opening.hr_status,
                    "job_state": opening.job_state,
                    "accepts_applications": True,
                }
            )

        return Response(
            {
                "count": len(payload),
                "results": payload,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="open",
        permission_classes=[CanToggleJobState],
        authentication_classes=[CsrfExemptSessionAuthentication],
    )
    def open(self, request, pk=None):
        opening = self.get_object()
        if opening.job_state == JobState.OPEN:
            return Response(
                {"detail": "Job is already open.", "job_state": opening.job_state},
                status=status.HTTP_200_OK,
            )
        opening.job_state = JobState.OPEN
        opening.save(update_fields=["job_state", "updated_at"])
        return Response(
            {"detail": "Job opened successfully.", "job_state": opening.job_state},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="close",
        permission_classes=[CanToggleJobState],
        authentication_classes=[CsrfExemptSessionAuthentication],
    )
    def close(self, request, pk=None):
        opening = self.get_object()
        if opening.job_state == JobState.CLOSED:
            return Response(
                {"detail": "Job is already closed.", "job_state": opening.job_state},
                status=status.HTTP_200_OK,
            )
        opening.job_state = JobState.CLOSED
        opening.save(update_fields=["job_state", "updated_at"])
        return Response(
            {"detail": "Job closed successfully.", "job_state": opening.job_state},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="apply",
        permission_classes=[AllowAny],
        authentication_classes=[CsrfExemptSessionAuthentication],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def apply(self, request, pk=None):
        """GET: API hint. POST: submit one application (multipart: ``full_name``, ``resume``)."""
        opening = self.get_object()
        if request.method == "GET":
            if not requirement_accepts_applications(opening):
                return Response(
                    {"detail": "Job is not available for application."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            # Build requirement_details only when both MD & HR approved
            requirement_details = None
            if requirement_accepts_applications(opening):
                from .serializers import JobApplicationNestedSerializer

                qs = opening.applications.all()
                requirement_details = JobApplicationNestedSerializer(
                    qs, many=True, context={"request": request},
                ).data

            return Response(
                {
                    "id": opening.pk,
                    "title": opening.title,
                    "department": opening.department,
                    "team": opening.team,
                    "type": opening.employment_type,
                    "num_positions": opening.num_positions,
                    "required_experience": opening.required_experience,
                    "primary_skills": opening.primary_skills,
                    "education": opening.education,
                    "tools_tech": opening.tools_tech,
                    "md_status": opening.md_status,
                    "hr_status": opening.hr_status,
                    "job_state": opening.job_state,
                    "requirement_details": requirement_details,
                },
                status=status.HTTP_200_OK,
            )
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if "fullName" in data and "full_name" not in data:
            data["full_name"] = data["fullName"]

        ser = JobApplySerializer(
            data=data,
            context={"request": request, "requirement": opening},
        )
        ser.is_valid(raise_exception=True)
        app = ser.save()
        return Response(
            {
                "id": app.id,
                "full_name": app.full_name,
                "applied_at": app.applied_at,
                "applied_by_username": app.applied_by.username if app.applied_by_id else None,
                "resume_url": request.build_absolute_uri(app.resume.url)
                if app.resume
                else None,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="apply-batch",
        permission_classes=[AllowAny],
        authentication_classes=[CsrfExemptSessionAuthentication],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def apply_batch(self, request, pk=None):
        """
        GET: API hint. POST: submit multiple applications in one request.

        Use ``multipart/form-data`` with **repeated** fields (same order):

        - ``full_name`` — once per applicant (e.g. ``getlist`` / multiple ``append`` in FormData)
        - ``resume`` — one file per applicant, parallel to names

        Example (3 applicants): 3× ``full_name``, 3× ``resume``.
        """
        opening = self.get_object()
        if request.method == "GET":
            return Response(
                {
                    "detail": "Submit with POST using multipart/form-data (not GET).",
                    "method": "POST",
                    "content_type": "multipart/form-data",
                    "fields": {
                        "full_name": "repeat once per applicant (same order as resume)",
                        "resume": "repeat one file per applicant",
                    },
                    "max_applicants_per_request": _APPLY_BATCH_MAX,
                    "job_id": opening.pk,
                    "accepts_applications": requirement_accepts_applications(opening),
                },
                status=status.HTTP_200_OK,
            )
        if not requirement_accepts_applications(opening):
            return Response(
                {
                    "detail": "Applications are only accepted for openings approved by both MD and HR."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(request.data, "getlist"):
            names = request.data.getlist("full_name")
            if not names:
                names = request.data.getlist("fullName")
        else:
            names = request.data.get("full_name")
            if names is None:
                names = request.data.get("fullName", [])
            if isinstance(names, str):
                names = [names]
        
        resumes = request.FILES.getlist("resume")
        if not names and not resumes:
            return Response(
                {
                    "detail": "Send at least one pair of full_name and resume (repeated form fields)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(names) != len(resumes):
            return Response(
                {
                    "detail": (
                        f"full_name count ({len(names)}) must match resume count ({len(resumes)})."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        n = len(names)
        if n > _APPLY_BATCH_MAX:
            return Response(
                {
                    "detail": f"At most {_APPLY_BATCH_MAX} applicants per request ({n} provided)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        applied_by = request.user if request.user.is_authenticated else None
        results = []

        with transaction.atomic():
            for raw_name, file_obj in zip(names, resumes):
                name = (raw_name or "").strip()
                if not file_obj or not getattr(file_obj, "name", None):
                    return Response(
                        {"detail": "Each applicant must include a resume file."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                app = JobApplication.objects.create(
                    requirement=opening,
                    full_name=name,
                    resume=file_obj,
                    applied_by=applied_by,
                )
                results.append(app)

        payload = []
        for app in results:
            payload.append(
                {
                    "id": app.id,
                    "full_name": app.full_name,
                    "applied_at": app.applied_at,
                    "applied_by_username": app.applied_by.username
                    if app.applied_by_id
                    else None,
                    "resume_url": request.build_absolute_uri(app.resume.url)
                    if app.resume
                    else None,
                }
            )

        return Response(
            {
                "created_count": len(payload),
                "applications": payload,
            },
            status=status.HTTP_201_CREATED,
        )
