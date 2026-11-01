from django.urls import path

from apps.m02_sedes.views import SedeListView

urlpatterns = [
    path("", SedeListView.as_view(), name="sede-list"),
]

