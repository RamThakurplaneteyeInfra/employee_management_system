from django.http import HttpRequest,HttpResponse
from django.http.response import JsonResponse

def home(request:HttpRequest):
    return JsonResponse({"messege":"You are at home"})