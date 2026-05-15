from datetime import datetime, timedelta

from django.http import JsonResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from .models import Asset
from .serializers import AssetSerializer


def health(_request):
    return JsonResponse({"status": "ok"})


def calendar_summary(request):
    """
    Returns booking counts per day for a given month.
    Query params:
      - year: YYYY
      - month: 1-12
      - asset_name (optional): filter to a single asset name
    """
    try:
        year = int(request.GET.get("year", ""))
        month = int(request.GET.get("month", ""))
    except ValueError:
        return JsonResponse(
            {"detail": "year and month are required integers"},
            status=400,
        )

    if month < 1 or month > 12:
        return JsonResponse({"detail": "month must be 1-12"}, status=400)

    first_day = datetime(year, month, 1, 0, 0, 0)
    if timezone.is_naive(first_day):
        first_day = timezone.make_aware(first_day, timezone.get_current_timezone())

    # first day of next month
    if month == 12:
        next_month = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        next_month = datetime(year, month + 1, 1, 0, 0, 0)
    if timezone.is_naive(next_month):
        next_month = timezone.make_aware(next_month, timezone.get_current_timezone())

    qs = Asset.objects.all()
    asset_name = request.GET.get("asset_name")
    if asset_name:
        qs = qs.filter(asset_name=asset_name)

    # Only assets that overlap the month window at all
    qs = qs.filter(start_at__lt=next_month, end_at__gt=first_day)

    # Simple capacity model to match UI "available"
    total_capacity = 36

    out = {}
    cur = first_day
    while cur < next_month:
        day_start = cur
        day_end = cur + timedelta(days=1)
        booked = qs.filter(start_at__lt=day_end, end_at__gt=day_start).count()
        key = day_start.date().isoformat()
        out[key] = {"booked": booked, "available": max(0, total_capacity - booked)}
        cur = day_end

    return JsonResponse(
        {
            "year": year,
            "month": month,
            "capacity": total_capacity,
            "days": out,
        }
    )


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer

    def get_queryset(self):
        qs = Asset.objects.all().order_by("-created_at")

        on_date = self.request.query_params.get("on_date")
        if on_date:
            try:
                y, m, d = [int(x) for x in on_date.split("-")]
                day_start = datetime(y, m, d, 0, 0, 0)
            except Exception as exc:
                raise ValidationError(
                    {"on_date": "Use format YYYY-MM-DD"}
                ) from exc

            if timezone.is_naive(day_start):
                day_start = timezone.make_aware(
                    day_start, timezone.get_current_timezone()
                )
            day_end = day_start + timedelta(days=1)

            qs = qs.filter(start_at__lt=day_end, end_at__gt=day_start)

        return qs
