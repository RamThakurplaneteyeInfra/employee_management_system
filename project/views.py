"""
Project API views. Base path: {{baseurl}}/projectapi/
- GET /products/ — list all products (id, name, description). Auth required.
- POST /products/create/ — create a product (name required; description optional). Auth required.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from asgiref.sync import sync_to_async

from django.views.decorators.csrf import csrf_exempt
from ems.verify_methods import verifyGet, verifyPost, load_data
from accounts.snippet import login_required
from ems.RequiredImports import status

from .models import Product


def _product_list_sync():
    """Return list of all products (id, name, description) for API."""
    return list(
        Product.objects.all().order_by("name").values("id", "name", "description")
    )


@login_required
@require_GET
async def product_list(request):
    """GET: List all products (id, name, description). Used by QuaterlyReports and clients."""
    if verifyGet(request):
        return verifyGet(request)
    data = await sync_to_async(_product_list_sync)()
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)


def _product_create_sync(name, description=None):
    """Create a product; returns (product_dict, None) or (None, error_response)."""
    name = (name or "").strip()
    if not name:
        return None, JsonResponse({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
    if Product.objects.filter(name__iexact=name).exists():
        return None, JsonResponse({"error": "A product with this name already exists"}, status=status.HTTP_409_CONFLICT)
    product = Product.objects.create(name=name, description=description or "")
    return {"id": product.id, "name": product.name, "description": product.description or ""}, None


@csrf_exempt
@login_required
@require_POST
async def product_create(request):
    """POST: Create a product. Body: {"name": "...", "description": "..."} (description optional)."""
    if verifyPost(request):
        return verifyPost(request)
    try:
        data = load_data(request)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    name = data.get("name")
    description = data.get("description")
    result, err = await sync_to_async(_product_create_sync)(name, description)
    if err:
        return err
    return JsonResponse(result, status=status.HTTP_201_CREATED)
