from ems.auth_utils import CsrfExemptSessionAuthentication
from rest_framework.viewsets import ModelViewSet
from .permissions import *
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from events.permissions import IsAdminOrMD
from rest_framework.permissions import IsAuthenticated,AllowAny
from .models import *
from .serializers import *

class BookSlotViewSet(ModelViewSet):
    queryset = BookSlot.objects.all()
    serializer_class = BookSlotSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        # 1. Open to everyone for GET requests (list and retrieve)
        if self.action in ['list', 'retrieve','create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        
        else:
            permission_classes = [AllowAny]
            
        return [permission() for permission in permission_classes]
    
    
    def perform_create(self, serializer):
        # This will override/ensure the created_by field is the logged-in user
        serializer.save(created_by=self.request.user)
        
    # def perform_update(self, serializer):
    #     # This will override/ensure the created_by field is the logged-in user
    #     serializer.save(created_by=self.request.user)

class RoomViewSet(ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes=[AllowAny]

class BookingStatusViewset(ModelViewSet):
    queryset = BookingStatus.objects.all()
    serializer_class = BookingStatusSerializer
    # authentication_classes = [CsrfExemptSessionAuthentication]

class TourViewSet(ModelViewSet):
    queryset = Tour.objects.all()
    serializer_class = TourSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes=[IsAuthenticated]

class HolidayViewSet(ModelViewSet):
    queryset = Holiday.objects.all().order_by("date")
    serializer_class = HolidaySerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    # permission_classes = [IsAuthenticated,IsAdminOrMD] 
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        # 1. Open to everyone for GET requests (list and retrieve)
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
            
        # 2. Restrict POST, PUT, PATCH, DELETE to Superusers only
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAdminOrMD]
            
        # 3. Default fallback (e.g., must be logged in)
        else:
            permission_classes = [AllowAny]
            
        return [permission() for permission in permission_classes]

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

class EventViewSet(ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]

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