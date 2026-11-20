from django.urls import path

from apps.m03_catalogo.admin_views import (
    CatalogoImagenView,
    CatalogoParametrosView,
    ExportarProductosView,
    HistorialPreciosView,
    ImportarProductosView,
    ParametroDetalleView,
    PlantillaImportView,
    ProductoAdminDetailView,
    ProductoAdminListCreateView,
    ProductoEstadoView,
    ProductoMediaView,
)

urlpatterns = [
    path("productos/", ProductoAdminListCreateView.as_view(), name="catalogo-productos"),
    path("productos/exportar/", ExportarProductosView.as_view(), name="catalogo-exportar"),
    path("productos/importar/", ImportarProductosView.as_view(), name="catalogo-importar"),
    path("productos/plantilla/", PlantillaImportView.as_view(), name="catalogo-plantilla"),
    path("productos/<int:pk>/", ProductoAdminDetailView.as_view(), name="catalogo-producto"),
    path("productos/<int:pk>/estado/", ProductoEstadoView.as_view(), name="catalogo-estado"),
    path("productos/<int:pk>/imagen/", CatalogoImagenView.as_view(), name="catalogo-imagen"),
    path("productos/<int:pk>/historial/", HistorialPreciosView.as_view(), name="catalogo-historial"),
    path("parametros/<str:tipo>/", CatalogoParametrosView.as_view(), name="catalogo-parametros"),
    path("parametros/<str:tipo>/<int:pk>/", ParametroDetalleView.as_view(), name="catalogo-parametro"),
    path("media/<path:ruta>/", ProductoMediaView.as_view(), name="catalogo-media"),
]
