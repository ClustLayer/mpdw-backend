"""Vistas sedes — público y gestión."""

from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


def _cliente_admin(db) -> APIClient:
    rol = Roles.objects.get(nombre="Administrador")
    user = Usuarios.objects.create_user(
        email="sedes.admin@test.local",
        password="Admin#2026demo",
        nombre="S",
        apellido="A",
        documento="100009990124",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email,
        "Admin#2026demo",
        "127.0.0.1",
        "pytest",
        "corr-sedes",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client


@pytest.mark.unit
@pytest.mark.django_db
def test_public_branches_list(db):
    client = APIClient()
    assert client.get("/api/v1/branches/").status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_gestion_paginacion_invalida(db):
    client = _cliente_admin(db)
    assert client.get("/api/v1/sedes/gestion/?page=x").status_code == 400


@pytest.mark.unit
@pytest.mark.django_db
def test_api_crear_y_editar_sede(db):
    client = _cliente_admin(db)
    c = client.post(
        "/api/v1/sedes/gestion/",
        {"nombre": "API", "direccion": "Calle", "telefono": "+573001234567"},
        format="json",
    )
    assert c.status_code == 201
    id_sede = c.json()["id_sede"]
    v = c.json()["version_fila"]
    p = client.patch(
        f"/api/v1/sedes/gestion/{id_sede}/",
        {"nombre": "API 2", "direccion": "Calle", "telefono": "+573001234567", "version_fila": v},
        format="json",
    )
    assert p.status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_consolidado_query(db):
    client = _cliente_admin(db)
    assert client.get("/api/v1/sedes/consolidado/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31").status_code == 200
