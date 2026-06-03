from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile

from .models import FarmServiceRequest
from .permissions import CanEditFarmServiceRequest
from .serializers import (
    EmployeeDropdownSerializer,
    FarmServiceRequestListSerializer,
    FarmServiceRequestSerializer,
)


class FarmServiceRequestViewSet(viewsets.ModelViewSet):
    """
    Isolated API for farm service task capture.
    PATCH replaces the nested task/subtask lists when `tasks` is included.
    DELETE on nested paths removes a single task or subtask (see delete_task / delete_subtask).
    """

    serializer_class = FarmServiceRequestSerializer
    permission_classes = [IsAuthenticated, CanEditFarmServiceRequest]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]
    queryset = FarmServiceRequest.objects.select_related("created_by").prefetch_related(
        "tasks__team_members",
        "tasks__subtasks__assigned_member",
        "tasks__subtasks__created_by",
    )

    def get_serializer_class(self):
        if self.action == "list":
            return FarmServiceRequestListSerializer
        return FarmServiceRequestSerializer

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

    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "detail": (
                    "Deleting the whole request is not supported. "
                    "Use DELETE .../tasks/{task_id}/ or PATCH with an updated tasks list."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"tasks/(?P<task_pk>\d+)",
    )
    def delete_task(self, request, pk=None, task_pk=None):
        request_obj = self.get_object()
        task = request_obj.tasks.filter(pk=task_pk).first()
        if task is None:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        task.delete()
        request_obj.refresh_from_db()
        serializer = FarmServiceRequestSerializer(request_obj, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"tasks/(?P<task_pk>\d+)/subtasks/(?P<subtask_pk>\d+)",
    )
    def delete_subtask(self, request, pk=None, task_pk=None, subtask_pk=None):
        request_obj = self.get_object()
        task = request_obj.tasks.filter(pk=task_pk).first()
        if task is None:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        subtask = task.subtasks.filter(pk=subtask_pk).first()
        if subtask is None:
            return Response({"detail": "Subtask not found."}, status=status.HTTP_404_NOT_FOUND)
        subtask.delete()
        request_obj.refresh_from_db()
        serializer = FarmServiceRequestSerializer(request_obj, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="employees")
    def employees(self, request):
        q = (request.query_params.get("q") or "").strip()
        qs = Profile.objects.all()
        if q:
            qs = qs.filter(Q(Employee_id_id__icontains=q) | Q(Name__icontains=q))
        qs = qs.order_by("Name")[:100]
        return Response(EmployeeDropdownSerializer(qs, many=True).data, status=status.HTTP_200_OK)

