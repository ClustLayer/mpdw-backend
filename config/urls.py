# ==============================================================================
# Enrutador Principal de la API REST - MPDW
# SAD Ref: §9.1, K-02
# ==============================================================================
from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Documentación OpenAPI 3.0 (Esquema crudo)
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Rutas por Módulo de Dominio
    path("api/v1/health/", include("apps.m13_plataforma.urls")),
    path("api/v1/auth/", include("apps.m01_identidad.urls")),
    path("api/v1/usuarios/", include("apps.m01_identidad.urls_usuarios")),
    path("api/v1/roles-permisos/", include("apps.m01_identidad.urls_roles_permisos")),
    path("api/v1/branches/", include("apps.m02_sedes.urls")),
    path("api/v1/sedes/", include("apps.m02_sedes.urls")),
    path("api/v1/products/", include("apps.m03_catalogo.urls")),
    path("api/v1/catalogo/", include("apps.m03_catalogo.urls_admin")),
    path("api/v1/inventory/", include("apps.m04_inventario.urls")),
    path("api/v1/inventario/", include("apps.m04_inventario.urls_admin")),
    path("api/v1/clientes/", include("apps.m05_clientes.urls_admin")),
    path("api/v1/auditoria/", include("apps.m10_auditoria.urls")),
]

# Swagger UI interactivo habilitado exclusivamente en entorno de desarrollo (SAD §9.1)
if getattr(settings, "DEBUG", False):
    urlpatterns.append(
        path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui")
    )

