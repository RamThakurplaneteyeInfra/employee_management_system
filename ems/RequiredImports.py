from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpRequest, JsonResponse, Http404
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from accounts.snippet import login_required, csrf_exempt
import json
import os
from datetime import date, timedelta, time, datetime
from ems.settings import BASE_DIR
from rest_framework import status
from django.contrib.auth.hashers import get_hasher
from django.utils.timezone import localtime
from django.db.models import Q, F
import requests
from django.db import DatabaseError, OperationalError, transaction

