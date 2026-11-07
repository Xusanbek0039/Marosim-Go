from django.urls import path

from .views import ChangelogView, EndpointsView, MobileGuideView, OverviewView

urlpatterns = [
    path("overview/", OverviewView.as_view(), name="devcenter-overview"),
    path("endpoints/", EndpointsView.as_view(), name="devcenter-endpoints"),
    path("mobile/", MobileGuideView.as_view(), name="devcenter-mobile"),
    path("changelog/", ChangelogView.as_view(), name="devcenter-changelog"),
]
