"""Version 1 of the public REST API (shared by the web panel and the mobile apps)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import AdminViewSet, UserViewSet
from apps.ceremonies.views import (
    CeremonyViewSet,
    InvitationViewSet,
    MyCeremonyViewSet,
    StudioMeCeremoniesView,
    StudioMeView,
)
from apps.monitoring.health import LiveView, ReadyView
from apps.studios.views import StudioViewSet
from apps.venues.admin_views import AdminVenueViewSet
from apps.venues.views import VenueOwnerVenueViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("users", UserViewSet, basename="user")
router.register("admins", AdminViewSet, basename="admin")
router.register("studios", StudioViewSet, basename="studio")
router.register("ceremonies", CeremonyViewSet, basename="ceremony")
router.register("me/ceremonies", MyCeremonyViewSet, basename="my-ceremony")
router.register("me/invitations", InvitationViewSet, basename="my-invitation")
router.register("venue-owner/venues", VenueOwnerVenueViewSet, basename="venue-owner-venue")
router.register("admin/venues", AdminVenueViewSet, basename="admin-venue")

urlpatterns = [
    path("auth/", include("apps.accounts.auth_urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("monitoring/", include("apps.monitoring.urls")),
    path("devcenter/", include("apps.devcenter.urls")),
    path("admin/storage/", include("apps.storage.urls")),
    path("health/live/", LiveView.as_view(), name="health-live"),
    path("health/ready/", ReadyView.as_view(), name="health-ready"),
    # Before the router: "studios/me/" must not be captured by "studios/{id}/".
    path("studios/me/", StudioMeView.as_view(), name="studio-me"),
    path("studios/me/ceremonies/", StudioMeCeremoniesView.as_view(), name="studio-me-ceremonies"),
    path("ceremonies/<uuid:ceremony_id>/media/", include("apps.media.urls")),
    path("me/ceremonies/<uuid:ceremony_id>/media/", include("apps.media.urls_me")),
    path("", include(router.urls)),
]
