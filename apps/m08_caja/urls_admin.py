from django.urls import path

from apps.m08_caja.admin_views import CuentaDetailView, CuentasActivasView, CuentasListCreateView

urlpatterns = [
    path("cuentas/activas/", CuentasActivasView.as_view(), name="cuentas-activas"),
    path("cuentas/", CuentasListCreateView.as_view(), name="cuentas-list-create"),
    path("cuentas/<int:id_cuenta>/", CuentaDetailView.as_view(), name="cuentas-detalle"),
]
