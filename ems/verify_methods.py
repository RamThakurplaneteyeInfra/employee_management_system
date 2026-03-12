from ems.RequiredImports import *
# to verify POST request
# use in the view that has been passed in the respective path function of the requested url.
def verifyPost(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    else:
        return None

# to verify GET request
# use in the view that has been passed in the respective path function of the requested url.
def verifyGet(request: HttpRequest):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    else:
        return None

# to verify PATCH request
# use in the view that has been passed in the respective path function of the requested url.
def verifyPatch(request: HttpRequest):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    else:
        return None

# to verify PUT request
# use in the view that has been passed in the respective path function of the requested url.
def verifyPut(request: HttpRequest):
    if request.method != "PUT":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    else:
        return None

# to verify DELETE request 
# use in the view that has been passed in the respective path function of the requested url.
def verifyDelete(request: HttpRequest):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    else:
        return None

# to load data from an incoming request
# use in the view that receives requests of the method POST, PUT, PATCH.
def load_data(request: HttpRequest):
    if request.content_type=="application/json":
        request_data=json.loads(request.body)
    else:
        request_data=request.POST
    return request_data

# If there are files, use the below one to load
def load_files_data(request: HttpRequest):
    data=request.FILES
    if data:
        return data
    return None
