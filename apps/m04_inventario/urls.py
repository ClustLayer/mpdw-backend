from django.urls import path

from apps.m04_inventario.views import InventarioListView

urlpatterns = [
    path("", InventarioListView.as_view(), name="inventario-list"),
]

