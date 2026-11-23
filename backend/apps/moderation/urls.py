from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AdminIdentityViewSet, AdminOverviewView, AdminPropertyViewSet

router = DefaultRouter()
router.register("properties", AdminPropertyViewSet, basename="admin-property")
router.register("identities", AdminIdentityViewSet, basename="admin-identity")

urlpatterns = [
    path("overview/", AdminOverviewView.as_view(), name="admin-overview"),
    *router.urls,
]
