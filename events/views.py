from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.conf import settings

from ems.RequiredImports import *
from accounts.models import Profile
from ems.auth_utils import CsrfExemptSessionAuthentication
from .permissions import *
from events.permissions import IsAdminOrMD, IsAdminOrMDOrHR

# # # # # #  baseurl="http://localhost:8000"  # # # # # # # # # # # #
# Base path: {{baseurl}}/eventsapi/
from .models import (
    BookSlot,
    SlotMembers,
    Room,
    BookingStatus,
    Tour,
    tourmembers,
    Holiday,
    Event,
    Meeting,
)
from .serializers import *

# Note: DRF ViewSets do not support async methods - they don't await coroutines.
# Sync views work under ASGI; Django runs them in a thread pool automatically.


def holidays_ping(request):
    """Test endpoint: GET /eventsapi/holidays-ping/ - plain Django, no DRF/auth/DB."""
    return JsonResponse({"status": "ok", "message": "holidays route reachable"})


# ==================== BookSlotViewSet ====================
# URL: {{baseurl}}/eventsapi/book-slots/  | CRUD
# Queryset optimized: select_related for FKs, prefetch_related for slot members + profile to avoid N+1.
class BookSlotViewSet(ModelViewSet):
    queryset = (
        BookSlot.objects.all()
        .select_related("room", "status", "created_by__accounts_profile")
        .prefetch_related(
            Prefetch(
                "slotmembers",
                queryset=SlotMembers.objects.select_related("member__accounts_profile"),
            )
        )
        .order_by("-date", "-created_at")
    )
    serializer_class = BookSlotSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get_queryset(self):
        queryset = super().get_queryset()
        param_value = self.request.GET
        if param_value:
            query_month = param_value.get("month")
            query_year = param_value.get("year")
            current_date = date.today()
            month = query_month if query_month else current_date.month
            year = query_year if query_year else current_date.year
            queryset = queryset.filter(created_at__month=month, created_at__year=year)
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

    @action(detail=False, methods=["get"], url_path="today")
    def today_slots(self, request):
        """GET {{baseurl}}/eventsapi/bookslots/today/ – slots booked on the current date."""
        today = date.today()
        qs = self.queryset.filter(date=today)
        serializer = BookSlotSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

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
# Optimized: prefetch tour members + profile, select_related creator profile to avoid N+1.
class TourViewSet(ModelViewSet):
    queryset = (
        Tour.objects.all()
        .select_related("created_by__accounts_profile")
        .prefetch_related(
            Prefetch(
                "tourmembers",
                queryset=tourmembers.objects.select_related("member__accounts_profile"),
            )
        )
        .order_by("-starting_date", "-created_at")
    )
    serializer_class = TourSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]


# ==================== HolidayViewSet ====================
# URL: {{baseurl}}/eventsapi/holidays/  | CRUD
# Aligned with RoomViewSet (AllowAny) - other events endpoints work with this pattern
class HolidayViewSet(ModelViewSet):
    queryset = Holiday.objects.all().order_by("date")
    serializer_class = HolidaySerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def get_permissions(self):
        """
        Assigns permissions based on the HTTP action.
        """
        if self.action in ['list', 'retrieve']:
            # Open to everyone
            return [IsAuthenticated()]
        
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Restrict to Admin, MD, or HR
            return [IsAuthenticated(), IsAdminOrMDOrHR()]
        else:
            return [AllowAny()]

# ==================== EventViewSet ====================
# URL: {{baseurl}}/eventsapi/events/  | CRUD
class EventViewSet(ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def get_permissions(self):
        """
        Assigns permissions based on the HTTP action.
        """
        if self.action in ['list', 'retrieve']:
            # Open to everyone
            return [IsAuthenticated()]
        
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Restrict to Admin, MD, or HR
            return [IsAuthenticated(), IsAdminOrMDOrHR()]
        else:
            return [AllowAny()]


# ==================== MeetingViewSet ====================
# URL: {{baseurl}}/eventsapi/meetingpush/  | CRUD
# Cron: {{baseurl}}/eventsapi/meetingpush/cron/delete-previous-days/  | GET (permissionless)
class MeetingViewSet(ModelViewSet):
    # Prefetch users with profile so serializer does not N+1 on get_user_details.
    User = get_user_model()
    queryset = (
        Meeting.objects.all()
        .select_related("meeting_room")
        .prefetch_related(Prefetch("users", queryset=User.objects.select_related("accounts_profile")))
    )
    serializer_class = MeetingSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get_permissions(self):
        """
        Assigns permissions based on the HTTP action.
        """
        if self.action in ["cron_delete_previous_days"]:
            return [AllowAny()]
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdminOrMDOrHR()]
        return [AllowAny()]

    @action(detail=False, methods=["get"], url_path="cron/delete-previous-days")
    def cron_delete_previous_days(self, request):
        """
        Delete meetings created on previous days (created_at date before today).
        Intended for cron; requires X-CRON-KEY header.
        """
        key = (request.META.get("HTTP_X_CRON_KEY") or "").strip()
        expected = getattr(settings, "X_CRON_KEY", "")
        if not expected or not constant_time_compare(key, expected):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        today = timezone.now().date()
        qs = Meeting.objects.filter(created_at__date__lt=today)
        count, _ = qs.delete()
        return Response({"deleted": count})
        
# ==================== birthdaycounter ====================
# GET only at .../birthdaycounter/<username>/ to fetch count.
# POST (update counts) only at .../birthdaycounter/ with body {"users": ["user1", "user2", ...]} (array may have one or more users).
# URL: {{baseurl}}/eventsapi/events/birthdaycounter/  (POST only) | {{baseurl}}/eventsapi/events/birthdaycounter/<username>/  (GET only)

def _birthdaycounter_get_sync(username):
    """Sync helper: fetch birthday_counter for one user."""
    user_obj = get_object_or_404(User, username=username)
    user_profile = Profile.objects.select_related("Employee_id").filter(Employee_id=user_obj).first()
    if not user_profile:
        raise Http404
    return {"birthday_counter": user_profile.birthday_counter}


def _birthdaycounter_bulk_post_sync(body):
    """
    Accept list of usernames in body["users"], increment birthday_counter on each user's Profile,
    then invalidate Redis GET cache for birthday_counter for all users so next GET returns fresh data.
    Returns {"updated": [{"username": u, "birthday_counter": n}, ...], "invalidated_cache": True}.
    """
    User = get_user_model()
    users_list = body.get("users") if isinstance(body, dict) else None
    if not users_list or not isinstance(users_list, list):
        return {"error": "Body must contain a list 'users' of usernames."}, 400
    updated = []
    with transaction.atomic():
        for username in users_list:
            if not username or not isinstance(username, str):
                continue
            username = username.strip()
            if not username:
                continue
            try:
                user_obj = User.objects.get(username=username)
            except User.DoesNotExist:
                continue
            profile = Profile.objects.filter(Employee_id=user_obj).first()
            if not profile:
                continue
            profile.birthday_counter += 1
            profile.save(update_fields=["birthday_counter"])
            updated.append({"username": username, "birthday_counter": profile.birthday_counter})
    if not updated:
        return {"error": "No valid users found or no profiles updated."}, 400
    # Erase Redis GET cache for birthday_counter so all clients see updated counts (works with KEY_PREFIX e.g. "ems")
    try:
        from ems.cache_utils import invalidate_birthday_counter_cache
        invalidate_birthday_counter_cache()
    except Exception:
        pass
    return {"updated": updated, "invalidated_cache": True}, 200


@csrf_exempt
async def birthdaycounter(request: HttpRequest, username=None):
    """GET only: fetch birthday_counter for the given username. Use POST .../birthdaycounter/ with body {\"users\": [\"username\"]} to update."""
    if request.method != "GET":
        return JsonResponse(
            {"error": "Method not allowed. Use POST /eventsapi/events/birthdaycounter/ with body {\"users\": [\"username\", ...]} to update."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
    try:
        result = await sync_to_async(_birthdaycounter_get_sync)(username)
        return JsonResponse(result, status=status.HTTP_200_OK)
    except Http404:
        return JsonResponse({"message": "user not found"}, status=status.HTTP_400_BAD_REQUEST)
    except DatabaseError as e:
        return JsonResponse({"message": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def birthdaycounter_bulk(request: HttpRequest):
    """
    POST with body {"users": ["username1", "username2", ...]}.
    Increments birthday_counter on each user's Profile, then invalidates the GET birthday_counter cache for all users.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    try:
        body = json.loads(request.body) if request.body else {}
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=status.HTTP_400_BAD_REQUEST)
    result, code = _birthdaycounter_bulk_post_sync(body)
    return JsonResponse(result, status=code)
        
# ******************************************************************** UNUSED APIS*****************************************************
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

# class HolidayViewSet(ModelViewSet):
    # queryset = Holiday.objects.all().order_by("date")
    # serializer_class = HolidaySerializer
    # authentication_classes = [CsrfExemptSessionAuthentication]
    # permission_classes=[AllowAny]
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