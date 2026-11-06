# ==============================================================================
# Rutas m10 auditoria - MPDW
# ==============================================================================
from django.urls import path

from apps.m10_auditoria.views import BitacoraListView, BitacoraUsuariosOpcionesView

urlpatterns = [
    path("bitacora/", BitacoraListView.as_view(), name="auditoria-bitacora-list"),
    path("bitacora/usuarios/", BitacoraUsuariosOpcionesView.as_view(), name="auditoria-bitacora-usuarios"),
]
