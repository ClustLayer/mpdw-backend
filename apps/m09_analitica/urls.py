from django.urls import path

from apps.m09_analitica.views import InteraccionesBatchView

urlpatterns = [
    path("interacciones/", InteraccionesBatchView.as_view(), name="analitica-interacciones"),
]
