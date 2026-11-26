from django.urls import path

from apps.m21_promociones.admin_views import (
    PromocionAdminDetailView,
    PromocionAdminListCreateView,
    PromocionImagenView,
)

urlpatterns = [
    path("", PromocionAdminListCreateView.as_view(), name="promociones-admin-list"),
    path("<int:pk>/", PromocionAdminDetailView.as_view(), name="promociones-admin-detail"),
    path("<int:pk>/imagen/", PromocionImagenView.as_view(), name="promociones-admin-imagen"),
]
