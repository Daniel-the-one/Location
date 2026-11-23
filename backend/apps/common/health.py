"""Endpoint de santé public et minimal, utilisé par le health check Render."""
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok"})
