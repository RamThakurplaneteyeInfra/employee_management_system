from django.core.exceptions import PermissionDenied
from accounts.filters import *
from django.http import HttpResponse,HttpRequest,JsonResponse,Http404
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
from accounts.models import *
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt,csrf_protect
import json
import os
from ems.settings import BASE_DIR
from rest_framework import status
from django.http.response import JsonResponse
from accounts.snippet import admin_required
from django.contrib.auth.hashers import get_hasher
from django.utils.timezone import localtime
from django.shortcuts import get_object_or_404
from django.db.models import Q,F

