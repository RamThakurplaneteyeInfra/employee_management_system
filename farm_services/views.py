from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile

from .models import FarmServiceRequest
from .permissions import CanEditFarmServiceRequest
from .serializers import EmployeeDropdownSerializer, FarmServiceRequestSerializer


class FarmServiceRequestViewSet(viewsets.ModelViewSet):
    """
    Isolated API for farm service task capture.
    No update/delete endpoints are exposed to avoid destructive operations.
    """

    serializer_class = FarmServiceRequestSerializer
    permission_classes = [IsAuthenticated, CanEditFarmServiceRequest]
    http_method_names = ["get", "post", "patch", "put", "head", "options"]
    queryset = FarmServiceRequest.objects.select_related("created_by").prefetch_related(
        "tasks__team_members"
    )

    def get_queryset(self):
        qs = super().get_queryset()
        service_name = (self.request.query_params.get("service_name") or "").strip()
        if service_name:
            qs = qs.filter(service_name__icontains=service_name)
        created_by = (self.request.query_params.get("created_by") or "").strip()
        if created_by:
            qs = qs.filter(created_by__username=created_by)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="employees")
    def employees(self, request):
        q = (request.query_params.get("q") or "").strip()
        qs = Profile.objects.all()
        if q:
            qs = qs.filter(Q(Employee_id_id__icontains=q) | Q(Name__icontains=q))
        qs = qs.order_by("Name")[:100]
        return Response(EmployeeDropdownSerializer(qs, many=True).data, status=status.HTTP_200_OK)

