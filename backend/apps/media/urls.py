"""Mounted at ``/api/v1/ceremonies/<ceremony_id>/media/`` (config/api_v1.py)."""

from django.urls import path

from .views import StudioMediaViewSet

urlpatterns = [
    path("", StudioMediaViewSet.as_view({"get": "list"}), name="ceremony-media-list"),
    path("uploads/", StudioMediaViewSet.as_view({"post": "start_upload"}), name="ceremony-media-upload"),
    path(
        "uploads/<uuid:media_id>/",
        StudioMediaViewSet.as_view({"get": "upload_status", "delete": "dismiss"}),
        name="ceremony-media-upload-status",
    ),
    path(
        "uploads/<uuid:media_id>/complete/",
        StudioMediaViewSet.as_view({"post": "complete"}),
        name="ceremony-media-upload-complete",
    ),
    path(
        "uploads/<uuid:media_id>/cancel/",
        StudioMediaViewSet.as_view({"post": "cancel"}),
        name="ceremony-media-upload-cancel",
    ),
    path(
        "<uuid:media_id>/delete-request/",
        StudioMediaViewSet.as_view({"post": "request_delete"}),
        name="ceremony-media-delete-request",
    ),
    path(
        "<uuid:media_id>/delete-request/cancel/",
        StudioMediaViewSet.as_view({"post": "cancel_delete"}),
        name="ceremony-media-delete-request-cancel",
    ),
]
