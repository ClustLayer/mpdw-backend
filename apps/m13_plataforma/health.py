# ==============================================================================
# Endpoints de Salud (Health Checks) - MPDW
# SAD Ref: I-12, ADR-012
# ==============================================================================
from typing import Any

from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.m13_plataforma.adapters.storage_supabase import SupabaseStorageAdapter


class HealthLiveView(APIView):
    """Liveness probe: indica si el proceso web de la API esta en ejecucion."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(
        summary="Liveness Probe",
        description="Indica si el servidor web HTTP está respondiendo.",
        responses={200: inline_serializer("LiveResponse", fields={"status": serializers.CharField()})},
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "live"}, status=status.HTTP_200_OK)


class HealthReadyView(APIView):
    """Readiness probe: verifica conectividad hacia PostgreSQL y Supabase Storage."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def __init__(self, storage_adapter: SupabaseStorageAdapter | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._storage_adapter = storage_adapter or SupabaseStorageAdapter()

    @extend_schema(
        summary="Readiness Probe",
        description="Verifica conectividad activa hacia PostgreSQL y Supabase Storage.",
        responses={
            200: inline_serializer(
                "ReadyResponse",
                fields={
                    "status": serializers.CharField(),
                    "database": serializers.CharField(),
                    "storage": serializers.CharField(),
                },
            ),
            503: inline_serializer(
                "NotReadyResponse",
                fields={
                    "status": serializers.CharField(),
                    "database": serializers.CharField(),
                    "storage": serializers.CharField(),
                },
            ),
        },
    )
    def get(self, request: Request) -> Response:
        db_ok = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_ok = True
        except Exception:
            db_ok = False

        try:
            storage_ok = self._storage_adapter.verificar_conexion()
        except Exception:
            storage_ok = False

        es_listo = db_ok and storage_ok
        payload = {
            "status": "ready" if es_listo else "not_ready",
            "database": "connected" if db_ok else "disconnected",
            "storage": "connected" if storage_ok else "disconnected",
        }
        codigo_http = status.HTTP_200_OK if es_listo else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=codigo_http)
