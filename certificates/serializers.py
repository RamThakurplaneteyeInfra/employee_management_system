from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.filters import _get_users_Name_sync
from .models import EmployeeCertificate
from .permissions import is_hr
from .s3_helpers import certificate_file_url, upload_certificate_file
from .services import create_certificate_record


def _resolve_owner_user(employee_id, request):
    """HR may set employeeId; others always use self."""
    if is_hr(request.user) and employee_id:
        username = str(employee_id).strip()
        if not username:
            raise serializers.ValidationError({"employeeId": ["employeeId cannot be empty."]})
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"employeeId": [f"No employee found with id '{username}'."]}
            )
    return request.user


class EmployeeCertificateReadSerializer(serializers.ModelSerializer):
    employeeId = serializers.CharField(source="employee.username", read_only=True)
    employeeName = serializers.SerializerMethodField()
    uploadedBy = serializers.CharField(
        source="uploaded_by.username", read_only=True, allow_null=True
    )
    fileUrl = serializers.SerializerMethodField()
    isActive = serializers.BooleanField(source="is_active", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = EmployeeCertificate
        fields = [
            "id",
            "employeeId",
            "employeeName",
            "uploadedBy",
            "title",
            "description",
            "file_name",
            "file_type",
            "file_size",
            "fileUrl",
            "isActive",
            "createdAt",
            "updatedAt",
        ]

    def get_employeeName(self, obj):
        profile = getattr(obj.employee, "accounts_profile", None)
        if profile and profile.Name:
            return profile.Name
        return _get_users_Name_sync(obj.employee) or obj.employee.username

    def get_fileUrl(self, obj):
        return certificate_file_url(obj.s3_key)


class EmployeeCertificateCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=500, default=""
    )
    employeeId = serializers.CharField(required=False, allow_blank=True)

    def validate_description(self, value):
        return (value or "").strip()[:500]

    def validate_title(self, value):
        return (value or "").strip()[:200]

    def create(self, validated_data):
        request = self.context["request"]
        owner = _resolve_owner_user(validated_data.pop("employeeId", None), request)
        record = create_certificate_record(
            owner,
            request.user,
            validated_data["file"],
            title=validated_data.get("title", ""),
            description=validated_data.get("description", ""),
        )
        record.save()
        return record


class EmployeeCertificateUpdateSerializer(serializers.ModelSerializer):
    """Metadata only; optional new file (old S3 object is not deleted)."""

    file = serializers.FileField(required=False, write_only=True)

    class Meta:
        model = EmployeeCertificate
        fields = ["title", "description", "file"]

    def validate_description(self, value):
        if value is None:
            return value
        return str(value).strip()[:500]

    def validate_title(self, value):
        if value is None:
            return value
        return str(value).strip()[:200]

    def update(self, instance, validated_data):
        file_obj = validated_data.pop("file", None)
        for field in ("title", "description"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        if file_obj is not None:
            instance.s3_key = upload_certificate_file(file_obj)
            instance.file_name = getattr(file_obj, "name", "") or instance.file_name
            instance.file_type = getattr(file_obj, "content_type", "") or instance.file_type
            instance.file_size = int(getattr(file_obj, "size", 0) or 0)
        instance.save()
        return instance
