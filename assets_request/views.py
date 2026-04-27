from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AssetRequest
from .permissions import IsAssetRequestAllowedRole, get_role_name
from .serializers import AssetRequestSerializer


class AssetRequestViewSet(viewsets.ModelViewSet):
    queryset = AssetRequest.objects.select_related("department", "assigned_to", "created_by")
    serializer_class = AssetRequestSerializer
    permission_classes = [IsAuthenticated, IsAssetRequestAllowedRole]

    def get_queryset(self):
        qs = super().get_queryset()
        role_name = get_role_name(self.request.user)
        if role_name == "TeamLead":
            return qs.filter(created_by=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Non-destructive: do not allow deleting requests via API.
        return Response(
            {"detail": "Delete is disabled for asset requests."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _enforce_field_permissions(self, request):
        role_name = get_role_name(request.user)
        incoming_fields = set(getattr(request, "data", {}).keys())

        protected_fields = {"admin_approval", "md_approval", "status", "assigned_to"}
        if not incoming_fields.intersection(protected_fields):
            return

        if "md_approval" in incoming_fields and role_name not in {"MD", "Admin"}:
            raise PermissionError("Only MD/Admin can update MD approval.")

        if "admin_approval" in incoming_fields and role_name not in {"Admin"}:
            raise PermissionError("Only Admin can update Admin approval.")

        if "assigned_to" in incoming_fields and role_name not in {"Hr", "Admin"}:
            raise PermissionError("Only HR/Admin can assign assets.")

        if "status" in incoming_fields and role_name not in {"Hr", "Admin"}:
            raise PermissionError("Only HR/Admin can update status.")

        if role_name == "TeamLead" and incoming_fields.intersection(protected_fields):
            raise PermissionError("TeamLead cannot update approvals/status/assignee.")

    def update(self, request, *args, **kwargs):
        try:
            self._enforce_field_permissions(request)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        try:
            self._enforce_field_permissions(request)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

