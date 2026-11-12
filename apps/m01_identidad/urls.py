from django.urls import path

from apps.m01_identidad.admin_roles_views import AccesosPanelView, PanelResumenView
from apps.m01_identidad.views import (
    CambiarContrasenaView,
    ContratoAuthView,
    LoginView,
    LogoutView,
    PoliticaSesionView,
    ProfileView,
    RecuperacionConfirmarView,
    RecuperacionSolicitudView,
    Reenviar2FAView,
    TokenRefreshView,
    Verificar2FAView,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("profile", ProfileView.as_view(), name="auth-profile"),
    path("politica-sesion", PoliticaSesionView.as_view(), name="auth-politica-sesion"),
    path("recuperar", RecuperacionSolicitudView.as_view(), name="auth-recuperar"),
    path("restablecer", RecuperacionConfirmarView.as_view(), name="auth-restablecer"),
    path("cambiar-contrasena", CambiarContrasenaView.as_view(), name="auth-cambiar-contrasena"),
    path("verificar-2fa", Verificar2FAView.as_view(), name="auth-verificar-2fa"),
    path("reenviar-2fa", Reenviar2FAView.as_view(), name="auth-reenviar-2fa"),
    path("contrato", ContratoAuthView.as_view(), name="auth-contrato"),
    path("accesos-panel", AccesosPanelView.as_view(), name="auth-accesos-panel"),
    path("panel-resumen", PanelResumenView.as_view(), name="auth-panel-resumen"),
]
