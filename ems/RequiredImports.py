"""
Universal import file for the EMS project.
Import from this module in app code to reduce redundancy and improve navigation.

Usage in apps:
    from ems.RequiredImports import *
    # or
    from ems.RequiredImports import HttpRequest, JsonResponse, status, get_object_or_404
"""

# -----------------------------------------------------------------------------
# Standard library
# -----------------------------------------------------------------------------
import asyncio
import json
import mimetypes
import os

# -----------------------------------------------------------------------------
# Django – URLs
# -----------------------------------------------------------------------------
from django.urls import path, include

# -----------------------------------------------------------------------------
# Django – HTTP
# -----------------------------------------------------------------------------
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    Http404,
    FileResponse,
)
from django.core.exceptions import PermissionDenied

# -----------------------------------------------------------------------------
# Django – Auth
# -----------------------------------------------------------------------------
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    get_user_model,
)
from django.contrib.auth.hashers import get_hasher

# -----------------------------------------------------------------------------
# Django – Shortcuts & DB
# -----------------------------------------------------------------------------
from django.shortcuts import render, redirect, get_object_or_404
from django.db import DatabaseError, OperationalError, transaction
from django.db.models import Q, F, Prefetch, Count
from django.utils.timezone import localtime

# -----------------------------------------------------------------------------
# Django – Validators (for models/serializers)
# -----------------------------------------------------------------------------
from django.core.validators import MinValueValidator, MaxValueValidator

# -----------------------------------------------------------------------------
# Django – Postgres (optional aggregates)
# -----------------------------------------------------------------------------
from django.contrib.postgres.aggregates import ArrayAgg

# -----------------------------------------------------------------------------
# Django – View decorators
# -----------------------------------------------------------------------------
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET

# -----------------------------------------------------------------------------
# Django – Signals (for use in app code)
# -----------------------------------------------------------------------------
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# -----------------------------------------------------------------------------
# Async
# -----------------------------------------------------------------------------
from asgiref.sync import sync_to_async

# -----------------------------------------------------------------------------
# Datetime
# -----------------------------------------------------------------------------
from datetime import date, timedelta, time, datetime

# -----------------------------------------------------------------------------
# Django REST framework
# -----------------------------------------------------------------------------
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import serializers

# -----------------------------------------------------------------------------
# Third-party
# -----------------------------------------------------------------------------
import requests

# -----------------------------------------------------------------------------
# Project – settings
# -----------------------------------------------------------------------------
from django.conf import settings

try:
    from ems.settings import BASE_DIR
except ImportError:
    BASE_DIR = None

# -----------------------------------------------------------------------------
# Project – app decorators (accounts.snippet)
# -----------------------------------------------------------------------------
from accounts.snippet import login_required, csrf_exempt
