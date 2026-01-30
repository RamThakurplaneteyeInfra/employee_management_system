from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Tour
from rest_framework.decorators import api_view

from .models import Holiday, BookSlot, Tour, Event
from .serializers import (
    HolidaySerializer,
    BookSlotSerializer,
    TourSerializer,
    EventSerializer
)

class BookSlotViewSet(ModelViewSet):
    queryset = BookSlot.objects.all()
    serializer_class = BookSlotSerializer
    permission_classes = [AllowAny]
    
@api_view(["GET"])
def rooms_dropdown(request):
    room = [
        {"key": "gateway"},
        {"key": "horizon"},
        {"key": "headquarter"},
        {"key": "synergy"},
    ]

    return Response({
        "status": "success",
        "data": room
    })

class TourViewSet(ModelViewSet):
    queryset = Tour.objects.all()
    serializer_class = TourSerializer
    permission_classes = [AllowAny]

class HolidayViewSet(ModelViewSet):
    queryset = Holiday.objects.all().order_by("date")
    serializer_class = HolidaySerializer
    permission_classes = [AllowAny]

    # ✅ /api/holidays/fixed/
    @action(detail=False, methods=["get"], url_path="fixed")
    def fixed_holidays(self, request):
        qs = self.queryset.filter(holiday_type="fixed")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # ✅ /api/holidays/unfixed/
    @action(detail=False, methods=["get"], url_path="unfixed")
    def unfixed_holidays(self, request):
        qs = self.queryset.filter(holiday_type="unfixed")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

class EventViewSet(ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
