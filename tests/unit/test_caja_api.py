from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


@pytest.mark.unit
@pytest.mark.django_db
def test_api_cuentas_bancarias() -> None:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="caja.api@test.local",
        password="Admin#2026demo",
        nombre="Caja",
        apellido="API",
        documento="100009990557",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-caja"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/caja/cuentas/activas/").status_code == 200
    lista = client.get("/api/v1/caja/cuentas/")
    assert lista.status_code == 200
    creada = client.post(
        "/api/v1/caja/cuentas/",
        {"nombre": "API Nequi", "tipo_cuenta": "Nequi", "numero": "3005554433", "estado": True},
        format="json",
    )
    assert creada.status_code in (200, 201)
    pk = creada.json()["item"]["id_cuenta_bancaria"]
    assert client.patch(
        f"/api/v1/caja/cuentas/{pk}/",
        {
            "nombre": "API Nequi",
            "tipo_cuenta": "Nequi",
            "numero": "3005554433",
            "estado": True,
            "version_fila": 1,
        },
        format="json",
    ).status_code == 200
