from django.urls import path

from apps.m21_promociones.admin_views import PromocionesPublicasView

urlpatterns = [
    path("", PromocionesPublicasView.as_view(), name="tienda-promociones"),
]
