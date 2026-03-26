"""
EMS root views.
Base URL: / (project root).
"""
from django.http import HttpRequest, HttpResponse
from django.http.response import JsonResponse


def home(request: HttpRequest):
    """
    GET /. Root endpoint; returns a simple JSON message.
    No auth required. Used as a health check or landing response.
    """
    return JsonResponse({"messege": "You are at home"})

import os
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

_METRICS_TOKEN = os.getenv("METRICS_AUTH_TOKEN", "").strip()


def metrics_view(request: HttpRequest):
    """GET /metrics — Prometheus scrape endpoint."""
    if _METRICS_TOKEN and request.META.get("HTTP_AUTHORIZATION", "") != f"Bearer {_METRICS_TOKEN}":
        return HttpResponse("Unauthorized", status=401)
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
