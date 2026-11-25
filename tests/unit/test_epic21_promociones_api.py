import io
from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from apps.m13_plataforma.observability.migration_backup import backup_rows, row_to_doc


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (12, 12), color=(10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def _client_admin() -> APIClient:
    rol, _ = Roles.objects.get_or_create(
        nombre="Administrador", defaults={"es_rol_base": True, "estado": True}
    )
    user = Usuarios.objects.create_user(
        email="promo.api@test.local",
        password="Admin#2026demo",
        nombre="Promo",
        apellido="API",
        documento="1000219901",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-promo"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client


@pytest.mark.unit
@pytest.mark.django_db
def test_api_promociones_crud_y_publico():
    client = _client_admin()
    inicio = timezone.now()
    creada = client.post(
        "/api/v1/promociones/",
        {
            "titulo": "API Promo",
            "tipo": "promocion",
            "descripcion": "Desc",
            "hashtags": "#api",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": (inicio + timezone.timedelta(days=2)).isoformat(),
            "estado": "activa",
        },
        format="json",
    )
    assert creada.status_code == 201
    pk = creada.json()["promocion"]["id_promocion"]
    assert client.get("/api/v1/promociones/").status_code == 200
    assert client.get(f"/api/v1/promociones/{pk}/").status_code == 200
    up = client.patch(
        f"/api/v1/promociones/{pk}/",
        {
            "titulo": "API Promo",
            "tipo": "promocion",
            "descripcion": "Desc 2",
            "hashtags": "#api",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": (inicio + timezone.timedelta(days=2)).isoformat(),
            "estado": "activa",
            "version_fila": 1,
        },
        format="json",
    )
    assert up.status_code == 200
    img = client.post(
        f"/api/v1/promociones/{pk}/imagen/",
        {"archivo": SimpleUploadedFile("p.png", _png(), content_type="image/png")},
        format="multipart",
    )
    assert img.status_code == 200
    pub = client.get("/api/v1/tienda/promociones/")
    assert pub.status_code == 200
    assert any(i["titulo"] == "API Promo" for i in pub.json()["items"])
    lote = client.post(
        "/api/v1/analitica/interacciones/",
        {"interacciones": [{"boton": "whatsapp_promo", "pantalla": "home", "id_promocion": pk}]},
        format="json",
    )
    assert lote.status_code == 200
    assert client.post("/api/v1/promociones/", {"titulo": ""}, format="json").status_code == 400
    assert (
        client.post(f"/api/v1/promociones/{pk}/imagen/", {}, format="multipart").status_code == 400
    )
    bad = APIClient().post(
        "/api/v1/analitica/interacciones/", {"interacciones": "x"}, format="json"
    )
    assert bad.status_code == 400
    assert client.get(f"/api/v1/promociones/{pk}/").status_code == 200
    assert (
        client.put(
            f"/api/v1/promociones/{pk}/",
            {
                "titulo": "API Promo",
                "tipo": "promocion",
                "descripcion": "Desc 3",
                "hashtags": "#api",
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": (inicio + timezone.timedelta(days=2)).isoformat(),
                "estado": "activa",
                "version_fila": up.json()["promocion"]["version_fila"],
            },
            format="json",
        ).status_code
        == 200
    )
    assert client.get("/api/v1/promociones/999999/").status_code == 404


@pytest.mark.unit
def test_migration_backup_sin_uri(monkeypatch):
    monkeypatch.delenv("MONGODB_GENERAL_URI", raising=False)

    class Row:
        id_auditoria = 9
        id_usuario_id = None
        accion = "CREAR_PRODUCTO"
        entidad = "Productos"
        id_entidad = 1
        motivo = "x"
        resultado = "EXITO"
        ip = "1.1.1.1"
        user_agent = "t"
        id_correlacion = "c"
        fecha_hora = None

    assert row_to_doc(Row())["accion"] == "CREAR_PRODUCTO"
    assert backup_rows([Row()]) == 1
    assert backup_rows([]) == 0
