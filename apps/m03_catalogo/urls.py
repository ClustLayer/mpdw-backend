from django.urls import path

from apps.m03_catalogo.views import ProductoListCreateView, ProductoPrecioUpdateView

urlpatterns = [
    path("", ProductoListCreateView.as_view(), name="producto-list-create"),
    path("<int:pk>/price", ProductoPrecioUpdateView.as_view(), name="producto-price-update"),
]

