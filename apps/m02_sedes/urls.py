from django.urls import path

from apps.m02_sedes.views import (
    SedeConsolidadoView,
    SedeDetailView,
    SedeListCreateView,
    SedePublicListView,
)

urlpatterns = [
    path("", SedePublicListView.as_view(), name="sede-public-list"),
    path("gestion/", SedeListCreateView.as_view(), name="sede-admin-list"),
    path("gestion/<int:id_sede>/", SedeDetailView.as_view(), name="sede-admin-detail"),
    path("consolidado/", SedeConsolidadoView.as_view(), name="sede-consolidado"),
]
