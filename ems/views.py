from django.http import HttpRequest,HttpResponse

def home(request:HttpRequest):
    return HttpResponse("You are at home")