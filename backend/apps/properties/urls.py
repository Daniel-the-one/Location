from django.urls import path
from rest_framework.routers import DefaultRouter

from .declarations import DeclarationView
from .views import OwnerPropertyViewSet, OwnerRoomViewSet, PropertyViewSet

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="property")
router.register("owner/properties", OwnerPropertyViewSet, basename="owner-property")
router.register("owner/rooms", OwnerRoomViewSet, basename="owner-room")

urlpatterns = [
    path("declarations/", DeclarationView.as_view(), name="declaration"),
    *router.urls,
]
