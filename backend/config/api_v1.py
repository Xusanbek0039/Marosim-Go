"""Version 1 of the public REST API (shared by the web panel and the mobile apps)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.policy_views import PlatformPolicyView
from apps.accounts.views import AdminViewSet, UserViewSet
from apps.ceremonies.views import (
    CeremonyViewSet,
    InvitationViewSet,
    MyCeremonyViewSet,
    StudioMeCeremoniesView,
    StudioMeView,
)
from apps.media.admin_views import AdminDeletionRequestViewSet
from apps.monitoring.health import LiveView, ReadyView
from apps.reviews.models import TargetKind
from apps.reviews.views import AdminReviewViewSet, LikeView, MyReviewView, TargetReviewsView
from apps.studios import public_views as studio_views
from apps.studios.public_views import PublicStudioViewSet, StudioMePortfolioImageView, StudioMePortfolioView
from apps.studios.views import StudioViewSet
from apps.subscriptions.views import (
    AdminPlanViewSet,
    AdminSettingsViewSet,
    AdminSubscriptionViewSet,
    MySubscriptionViewSet,
    PlanListViewSet,
)
from apps.support.applications import PublicApplicationViewSet, StaffApplicationViewSet
from apps.support.views import MySupportTicketViewSet, StaffSupportTicketViewSet
from apps.venues.admin_views import AdminVenueViewSet
from apps.venues.public_views import MyVenueBookingViewSet, PublicVenueViewSet
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
router.register("venues", PublicVenueViewSet, basename="venue")
router.register("public/studios", PublicStudioViewSet, basename="public-studio")
router.register("admin/reviews", AdminReviewViewSet, basename="admin-review")
router.register("subscriptions/plans", PlanListViewSet, basename="subscription-plan")
router.register("me/subscriptions", MySubscriptionViewSet, basename="my-subscription")
router.register("admin/subscriptions", AdminSubscriptionViewSet, basename="admin-subscription")
router.register("admin/subscription-plans", AdminPlanViewSet, basename="admin-subscription-plan")
router.register("me/venue-bookings", MyVenueBookingViewSet, basename="my-venue-booking")
router.register("admin/media-deletion-requests", AdminDeletionRequestViewSet, basename="admin-media-deletion-request")
router.register("support/tickets", MySupportTicketViewSet, basename="support-ticket")
router.register("admin/support/tickets", StaffSupportTicketViewSet, basename="admin-support-ticket")
router.register("admin/support/applications", StaffApplicationViewSet, basename="admin-partner-application")
router.register("public/partner-applications", PublicApplicationViewSet, basename="public-partner-application")

urlpatterns = [
    path(
        "admin/platform-policy/",
        PlatformPolicyView.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="platform-policy",
    ),
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
    path("studios/me/<uuid:studio_id>/images/", StudioMePortfolioView.as_view(), name="studio-me-images"),
    path("studios/me/<uuid:studio_id>/reels/", studio_views.StudioMeReelsView.as_view(), name="studio-me-reels"),
    path(
        "studios/me/<uuid:studio_id>/images/<uuid:image_id>/",
        StudioMePortfolioImageView.as_view(),
        name="studio-me-image",
    ),
    path(
        "studios/me/<uuid:studio_id>/images/<uuid:image_id>/comments/",
        studio_views.StudioMeCommentsView.as_view(),
        name="studio-me-image-comments",
    ),
    path(
        "studios/me/<uuid:studio_id>/images/<uuid:image_id>/comments/<uuid:comment_id>/",
        studio_views.StudioMeCommentView.as_view(),
        name="studio-me-image-comment",
    ),
    path("studios/me/<uuid:studio_id>/schedule/", studio_views.StudioMeScheduleView.as_view(), name="studio-me-schedule"),
    path(
        "studios/me/<uuid:studio_id>/schedule/days/<str:day>/",
        studio_views.StudioMeScheduleDayView.as_view(),
        name="studio-me-schedule-day",
    ),
    path("studios/me/<uuid:studio_id>/chats/", studio_views.StudioMeChatsView.as_view(), name="studio-me-chats"),
    path(
        "studios/me/<uuid:studio_id>/chats/<uuid:conversation_id>/",
        studio_views.StudioMeChatView.as_view(),
        name="studio-me-chat",
    ),
    # studio portfolio interactions and customer ↔ studio chat
    path(
        "public/studios/<uuid:studio_id>/portfolio/<uuid:item_id>/reaction/",
        studio_views.PortfolioReactionView.as_view(),
        name="studio-portfolio-reaction",
    ),
    path(
        "public/studios/<uuid:studio_id>/portfolio/<uuid:item_id>/comments/",
        studio_views.PortfolioCommentsView.as_view(),
        name="studio-portfolio-comments",
    ),
    path(
        "public/studios/<uuid:studio_id>/portfolio/<uuid:item_id>/comments/<uuid:comment_id>/",
        studio_views.PortfolioMyCommentView.as_view(),
        name="studio-portfolio-comment",
    ),
    path(
        "public/studios/<uuid:studio_id>/portfolio/<uuid:item_id>/file/<str:part>/",
        studio_views.PortfolioFileView.as_view(),
        name="studio-portfolio-file",
    ),
    path("studios/me/<uuid:studio_id>/storage/", studio_views.StudioMeStorageView.as_view(), name="studio-me-storage"),
    path("me/studio-chats/", studio_views.MyStudioChatsView.as_view(), name="my-studio-chats"),
    path("me/studio-chats/<uuid:studio_id>/", studio_views.MyStudioChatView.as_view(), name="my-studio-chat"),
    # reviews / likes of public venues and studios
    *[
        p
        for prefix, kind in (("venues", TargetKind.VENUE), ("public/studios", TargetKind.STUDIO))
        for p in (
            path(f"{prefix}/<uuid:target_id>/reviews/", TargetReviewsView.as_view(kind=kind), name=f"{kind}-reviews"),
            path(f"{prefix}/<uuid:target_id>/reviews/mine/", MyReviewView.as_view(kind=kind), name=f"{kind}-my-review"),
            path(f"{prefix}/<uuid:target_id>/like/", LikeView.as_view(kind=kind), name=f"{kind}-like"),
        )
    ],
    path("ceremonies/<uuid:ceremony_id>/media/", include("apps.media.urls")),
    path("me/ceremonies/<uuid:ceremony_id>/media/", include("apps.media.urls_me")),
    path(
        "admin/subscription-settings/",
        AdminSettingsViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="admin-subscription-settings",
    ),
    path("", include(router.urls)),
]
