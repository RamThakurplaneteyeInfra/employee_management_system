from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    Custom exception handler that standardizes the error response format.
    Format:
    {
        "success": False,
        "message": "Error message",
        "code": "error_code",
        "errors": { ... } (optional details)
    }
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If response is None, it means it's an exception DRF doesn't handle natively
    # (like a raw Python KeyError or ValueError). 
    # We can choose to handle them here or let Django's 500 handler take over.
    if response is not None:
        custom_data = {
            "success": False,
            "message": "An error occurred",
            "code": "error"
        }

        # Handle specific error codes if available
        if hasattr(exc, 'default_code'):
            custom_data["code"] = exc.default_code
        
        # Improve message based on the exception type
        if hasattr(exc, 'detail'):
            # If detail is a string, use it as the message
            if isinstance(exc.detail, str):
                custom_data["message"] = exc.detail
            # If detail is a list or dict (validation errors), put it in 'errors'
            else:
                custom_data["message"] = "Validation error"
                custom_data["errors"] = exc.detail
                custom_data["code"] = "validation_error"

        response.data = custom_data

    return response
