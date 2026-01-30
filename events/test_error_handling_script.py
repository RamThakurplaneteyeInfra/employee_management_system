# Configure Django settings (minimal needed for DRF)
from django.conf import settings
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from ems.utils import custom_exception_handler
from rest_framework.views import APIView

def test_custom_handler():
    factory = APIRequestFactory()
    request = factory.get('/')
    context = {'view': APIView}

    print("Testing custom exception handler...")

    # 1. Test ValidationError (String)
    exc = ValidationError("Invalid input")
    response = custom_exception_handler(exc, context)
    print("\n1. ValidationError (String):")
    print(response.data)
    assert response.data['success'] == False
    assert response.data['code'] == 'validation_error'
    assert 'errors' in response.data

    # 2. Test ValidationError (Dict/List)
    exc = ValidationError({"field": ["This field is required."]})
    response = custom_exception_handler(exc, context)
    print("\n2. ValidationError (Dict):")
    print(response.data)
    assert response.data['success'] == False
    assert response.data['code'] == 'validation_error'
    assert 'errors' in response.data

    # 3. Test NotFound
    exc = NotFound()
    response = custom_exception_handler(exc, context)
    print("\n3. NotFound:")
    print(response.data)
    assert response.data['success'] == False
    assert response.data['code'] == 'not_found'

    # 4. Test PermissionDenied
    exc = PermissionDenied()
    response = custom_exception_handler(exc, context)
    print("\n4. PermissionDenied:")
    print(response.data)
    assert response.data['success'] == False
    assert response.data['code'] == 'permission_denied'

    print("\nAll tests passed!")

if __name__ == "__main__":
    test_custom_handler()
