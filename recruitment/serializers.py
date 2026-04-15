from rest_framework import serializers

from .models import ApprovalStatus, JobApplication, JobOpening, JobState


def requirement_accepts_applications(opening: JobOpening | None) -> bool:
    """True when approved by MD+HR and job is operationally open."""
    if opening is None:
        return False
    return (
        opening.md_status == ApprovalStatus.APPROVED
        and opening.hr_status == ApprovalStatus.APPROVED
        and opening.job_state == JobState.OPEN
    )


def _absolute_media_url(request, file_field) -> str | None:
    if not file_field or not getattr(file_field, "name", None):
        return None
    url = file_field.url
    if url.startswith("http"):
        return url
    if request:
        return request.build_absolute_uri(url)
    return url


class JobApplicationNestedSerializer(serializers.ModelSerializer):
    """Applicants on a job detail (staff only)."""

    resume_url = serializers.SerializerMethodField()
    applied_by_username = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "full_name",
            "resume_url",
            "applied_at",
            "applied_by_username",
        )
        read_only_fields = fields

    def get_resume_url(self, obj):
        request = self.context.get("request")
        return _absolute_media_url(request, obj.resume)

    def get_applied_by_username(self, obj):
        if obj.applied_by_id:
            return obj.applied_by.username
        return None


class JobOpeningListSerializer(serializers.ModelSerializer):
    """Public list: no applicants, no internal-only noise."""

    type = serializers.CharField(source="employment_type", read_only=True)
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = JobOpening
        fields = (
            "id",
            "title",
            "department",
            "team",
            "type",
            "num_positions",
            "required_experience",
            "primary_skills",
            "education",
            "tools_tech",
            "md_status",
            "hr_status",
            "job_state",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_created_by_username(self, obj):
        if obj.created_by_id:
            return obj.created_by.username
        return None


class JobOpeningDetailSerializer(JobOpeningListSerializer):
    class Meta:
        model = JobOpening
        fields = JobOpeningListSerializer.Meta.fields
        read_only_fields = fields


class JobOpeningWriteSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="employment_type")
    created_by_username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JobOpening
        fields = (
            "id",
            "title",
            "department",
            "team",
            "type",
            "num_positions",
            "required_experience",
            "primary_skills",
            "education",
            "tools_tech",
            "md_status",
            "hr_status",
            "job_state",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by_username", "created_at", "updated_at")
        extra_kwargs = {
            "title": {"required": True},
            "department": {"required": True},
            "team": {"required": True},
        }

    def get_created_by_username(self, obj):
        if obj.pk and obj.created_by_id:
            return obj.created_by.username
        return None

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            validated_data["created_by"] = user
        # Keep create behavior stable: new jobs always start as Open.
        validated_data.pop("job_state", None)
        return super().create(validated_data)


class JobApplySerializer(serializers.ModelSerializer):
    """Multipart: full_name + resume."""

    full_name = serializers.CharField(required=True, allow_blank=False, max_length=200)

    class Meta:
        model = JobApplication
        fields = ("full_name", "resume")

    def validate(self, attrs):
        req = self.context.get("requirement")
        if req is None:
            raise serializers.ValidationError("Missing job opening.")
        if not requirement_accepts_applications(req):
            raise serializers.ValidationError(
                "Applications are only accepted for openings approved by both MD and HR."
            )
        return attrs

    def create(self, validated_data):
        requirement = self.context["requirement"]
        request = self.context.get("request")
        applied_by = None
        if request and request.user.is_authenticated:
            applied_by = request.user
        return JobApplication.objects.create(
            requirement=requirement,
            applied_by=applied_by,
            **validated_data,
        )
