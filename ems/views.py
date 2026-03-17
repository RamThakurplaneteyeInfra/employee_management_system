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