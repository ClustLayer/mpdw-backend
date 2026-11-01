from django.urls import path

from apps.m13_plataforma.health import HealthLiveView, HealthReadyView

urlpatterns = [
    path("live", HealthLiveView.as_view(), name="health-live"),
    path("ready", HealthReadyView.as_view(), name="health-ready"),
]

