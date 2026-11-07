"""Mounted at ``/api/v1/me/ceremonies/<ceremony_id>/media/`` (config/api_v1.py)."""

from django.urls import path

from .viewing import MyMediaViewSet

urlpatterns = [
    path("", MyMediaViewSet.as_view({"get": "list"}), name="my-ceremony-media-list"),
    path(
        "<uuid:media_id>/thumbnail/", MyMediaViewSet.as_view({"get": "thumbnail"}), name="my-ceremony-media-thumbnail"
    ),
    path("<uuid:media_id>/stream/", MyMediaViewSet.as_view({"get": "stream"}), name="my-ceremony-media-stream"),
    path("<uuid:media_id>/download/", MyMediaViewSet.as_view({"get": "download"}), name="my-ceremony-media-download"),
]
