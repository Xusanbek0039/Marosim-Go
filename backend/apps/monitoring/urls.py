from django.urls import path

from .views import EndpointCatalogView, OverviewView, RequestLogListView

urlpatterns = [
    path("overview/", OverviewView.as_view(), name="monitoring-overview"),
    path("logs/", RequestLogListView.as_view(), name="monitoring-logs"),
    path("endpoints/", EndpointCatalogView.as_view(), name="monitoring-endpoints"),
]
