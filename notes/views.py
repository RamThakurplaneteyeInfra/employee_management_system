from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ems.auth_utils import CsrfExemptSessionAuthentication

from .models import Note
from .serializers import NoteCreateItemSerializer, NoteSerializer


class NoteViewSet(ModelViewSet):
    """
    Personal notes for each user.

    Security:
    - All queries are filtered by created_by=request.user.
    - DELETE is implemented as a soft-delete (no physical row deletion).
    - Users cannot access other users' notes.
    """

    serializer_class = NoteSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Note.objects.filter(created_by=self.request.user, is_deleted=False)
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        payload = request.data

        # Bulk create: {"notes": [ {..}, {..} ]}
        if isinstance(payload, dict) and "notes" in payload:
            items = payload.get("notes")
            if not isinstance(items, list) or not items:
                return Response(
                    {"error": "notes must be a non-empty array"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item_serializer = NoteCreateItemSerializer(data=items, many=True)
            item_serializer.is_valid(raise_exception=True)

            to_create = []
            for item in item_serializer.validated_data:
                to_create.append(
                    Note(
                        title=item.get("title"),
                        content=str(item["content"]).strip(),
                        created_by=request.user,
                    )
                )

            with transaction.atomic():
                created = Note.objects.bulk_create(to_create)

            return Response(
                {
                    "message": f"{len(created)} note(s) created",
                    "notes": NoteSerializer(created, many=True).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # Single create: { "title": "...", "content": "..." }
        item_serializer = NoteCreateItemSerializer(data=payload)
        item_serializer.is_valid(raise_exception=True)
        note = Note.objects.create(
            title=item_serializer.validated_data.get("title"),
            content=str(item_serializer.validated_data["content"]).strip(),
            created_by=request.user,
        )
        return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: do not remove rows from the database.
        """
        instance = self.get_object()
        instance.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

