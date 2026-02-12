from django.core.exceptions import PermissionDenied
from django.http import HttpResponse,HttpRequest,JsonResponse,Http404
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt,csrf_protect
import json
import os
from datetime import date,timedelta,time,datetime
from ems.settings import BASE_DIR
from rest_framework import status
from django.contrib.auth.hashers import get_hasher
from django.utils.timezone import localtime
from django.shortcuts import get_object_or_404
from django.db.models import Q,F
import requests
from django.db import DatabaseError,OperationalError

