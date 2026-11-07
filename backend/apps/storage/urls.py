from django.urls import path

from .views import CallbackView, ConnectView, DisconnectView, StatusView, TestConnectionView

urlpatterns = [
    path("google/connect/", ConnectView.as_view(), name="storage-google-connect"),
    path("google/callback/", CallbackView.as_view(), name="storage-google-callback"),
    path("google/status/", StatusView.as_view(), name="storage-google-status"),
    path("google/test/", TestConnectionView.as_view(), name="storage-google-test"),
    path("google/disconnect/", DisconnectView.as_view(), name="storage-google-disconnect"),
]
