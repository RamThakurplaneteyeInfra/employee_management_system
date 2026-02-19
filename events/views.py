from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from ems.auth_utils import CsrfExemptSessionAuthentication
from rest_framework.viewsets import ModelViewSet
from .permissions import *
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from events.permissions import IsAdminOrMD

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #
# Base path: {{baseurl}}/eventsapi/
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import *
from .serializers import *

# Note: DRF ViewSets do not support async methods - they don't await coroutines.
# Sync views work under ASGI; Django runs them in a thread pool automatically.


def holidays_ping(request):
    """Test endpoint: GET /eventsapi/holidays-ping/ - plain Django, no DRF/auth/DB."""
    return JsonResponse({"status": "ok", "message": "holidays route reachable"})


# ==================== BookSlotViewSet ====================
# URL: {{baseurl}}/eventsapi/book-slots/  | CRUD
class BookSlotViewSet(ModelViewSet):
    queryset = BookSlot.objects.all().select_related("room","created_by","status")
    serializer_class = BookSlotSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        param_value = self.request.GET
        if param_value:
            query_month=param_value.get("month")
            query_year=param_value.get("year")
            current_date=date.today()
            month = query_month if query_month else current_date.month
            year = query_year if query_year else current_date.year
            queryset = queryset.filter(created_at__month=month,created_at__year=year)
        return queryset
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        # 1. Open to everyone for GET requests (list and retrieve)
        if self.action in ['list', 'retrieve','create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        
        else:
            permission_classes = [AllowAny]
            
        return [permission_classes[0]()]
    
    
    def perform_create(self, serializer):
        # This will override/ensure the created_by field is the logged-in user
        serializer.save(created_by=self.request.user)
        
    # def perform_update(self, serializer):
    #     # This will override/ensure the created_by field is the logged-in user
    #     serializer.save(created_by=self.request.user)


# ==================== RoomViewSet ====================
# URL: {{baseurl}}/eventsapi/rooms/  | CRUD
class RoomViewSet(ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes=[AllowAny]


# ==================== BookingStatusViewset ====================
# URL: {{baseurl}}/eventsapi/booking-statuses/  | CRUD
class BookingStatusViewset(ModelViewSet):
    queryset = BookingStatus.objects.all()
    serializer_class = BookingStatusSerializer
    # authentication_classes = [CsrfExemptSessionAuthentication]


# ==================== TourViewSet ====================
# URL: {{baseurl}}/eventsapi/tours/  | CRUD
class TourViewSet(ModelViewSet):
    queryset = Tour.objects.all()
    serializer_class = TourSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes=[IsAuthenticated]


# ==================== HolidayViewSet ====================
# URL: {{baseurl}}/eventsapi/holidays/  | CRUD
# Aligned with RoomViewSet (AllowAny) - other events endpoints work with this pattern
class HolidayViewSet(ModelViewSet):
    queryset = Holiday.objects.all().order_by("date")
    serializer_class = HolidaySerializer
    # authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes=[AllowAny]
    # def get_authenticators(self):
    #     """Skip auth for list/retrieve to avoid ASGI + SessionAuth hang (sync DB in async context)."""
    #     if self.action in ["list", "retrieve"]:
    #         return []
    #     return super().get_authenticators()

    # def get_permissions(self):
    #     if self.action in ["list", "retrieve"]:
    #         return [AllowAny()]
    #     elif self.action in ["create", "update", "partial_update", "destroy"]:
    #         return [IsAuthenticated(), IsAdminOrMD()]
    #     return [AllowAny()]

    # # ✅ /api/holidays/
    # @action(detail=False, methods=["get"], url_path="fixed")
    # def fixed_holidays(self, request):
    #     qs = self.queryset.filter(holiday_type="fixed")
    #     serializer = self.get_serializer(qs, many=True)
    #     return Response(serializer.data)

    # # ✅ /api/holidays/unfixed/
    # @action(detail=False, methods=["get"], url_path="unfixed")
    # def unfixed_holidays(self, request):
    #     qs = self.queryset.filter(holiday_type="unfixed")
    #     serializer = self.get_serializer(qs, many=True)
    #     return Response(serializer.data)


# ==================== EventViewSet ====================
# URL: {{baseurl}}/eventsapi/events/  | CRUD
class EventViewSet(ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]


# ==================== MeetingViewSet ====================
# URL: {{baseurl}}/eventsapi/meetings/  | CRUD
class MeetingViewSet(ModelViewSet):
    # Optimized query with prefetch for M2M users and select for ForeignKey room
    queryset = Meeting.objects.all().select_related('meeting_room').prefetch_related('users')
    serializer_class = MeetingSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def get_permissions(self):
        """
        Assigns permissions based on the HTTP action.
        """
        if self.action in ['list', 'retrieve']:
            # Open to everyone
            return [IsAuthenticated()]
        
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Restrict to Superusers only
            return [IsAuthenticated(),IsAdminOrMD()]
        else:
            return [AllowAny()]
        
# @api_view(["GET"])
# def rooms_dropdown(request):
#     rooms = Room.objects.filter(is_active=True)
#     serializer = RoomSerializer(rooms, many=True)
#     return Response({
#         "status": "success",
#         "data": serializer.data
#     })


# @api_view(["GET"])
# def status_dropdown(request):
#     status = BookingStatus.objects.filter(is_active=True)
#     serializer = BookingStatusSerializer(status, many=True)
#     return Response({
#         "status": "success",
#         "data": serializer.data
#     })

# @api_view(["GET"])
# def location_dropdown(request):
#     query = request.GET.get("q")
#     if not query:
#         return Response({"status": "success", "data": []})

#     url = "https://nominatim.openstreetmap.org/search"
#     params = {
#         "q": query,
#         "format": "json",
#         "limit": 8
#     }

#     headers = {
#         "User-Agent": "calendar-backend"
#     }

#     res = requests.get(url, params=params, headers=headers, timeout=5)
#     data = res.json()

#     results = [
#         {
#             "label": place["display_name"],
#             "value": place["display_name"]
#         }
#         for place in data
#     ]

#     return Response({
#         "status": "success",
#         "data": results
#     })