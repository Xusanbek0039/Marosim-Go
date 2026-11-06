"""Version 1 of the public REST API (shared by the web panel and future mobile apps)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import AdminViewSet, UserViewSet
from apps.studios.views import StudioViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("users", UserViewSet, basename="user")
router.register("admins", AdminViewSet, basename="admin")
router.register("studios", StudioViewSet, basename="studio")

urlpatterns = [
    path("auth/", include("apps.accounts.auth_urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("", include(router.urls)),
]
