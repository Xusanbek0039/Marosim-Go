"""Version 1 of the public REST API (shared by the web panel and the mobile apps)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import AdminViewSet, UserViewSet
from apps.monitoring.health import LiveView, ReadyView
from apps.studios.views import StudioViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("users", UserViewSet, basename="user")
router.register("admins", AdminViewSet, basename="admin")
router.register("studios", StudioViewSet, basename="studio")

urlpatterns = [
    path("auth/", include("apps.accounts.auth_urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("monitoring/", include("apps.monitoring.urls")),
    path("health/live/", LiveView.as_view(), name="health-live"),
    path("health/ready/", ReadyView.as_view(), name="health-ready"),
    path("", include(router.urls)),
]
