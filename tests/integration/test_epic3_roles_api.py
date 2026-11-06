"""Integracion API Epic 3."""

from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Permisos, Rol_permiso, Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


def _cliente(usuario: Usuarios, password: str = "Admin#2026demo") -> APIClient:
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        usuario.email,
        password,
        "127.0.0.1",
        "pytest",
        "corr-ep3",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client


def _otorgar_roles_permisos(rol: Roles) -> None:
    perm, _ = Permisos.objects.get_or_create(
        modulo="roles_permisos",
        accion="T",
        defaults={"nombre": "Roles T", "estado": True},
    )
    Rol_permiso.objects.update_or_create(id_rol=rol, id_permiso=perm, defaults={"permitido": True})


@pytest.fixture
def admin_user(db):
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    _otorgar_roles_permisos(rol)
    return Usuarios.objects.create_user(
        email="admin.ep3@test.local",
        password="Admin#2026demo",
        nombre="Admin",
        apellido="Ep3",
        documento="100008890123",
        id_rol=rol,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_api_crear_rol(admin_user):
    client = _cliente(admin_user)
    resp = client.post(
        "/api/v1/roles-permisos/roles",
        {"nombre": "RolAPI", "descripcion": "Desde test"},
        format="json",
    )
    assert resp.status_code == 201
    assert "correctamente" in resp.json()["mensaje"]


@pytest.mark.integration
@pytest.mark.django_db
def test_api_listar_permisos(admin_user):
    client = _cliente(admin_user)
    resp = client.get("/api/v1/roles-permisos/permisos?page=1")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.integration
@pytest.mark.django_db
def test_api_accesos_panel(admin_user):
    client = _cliente(admin_user)
    resp = client.get("/api/v1/auth/accesos-panel")
    assert resp.status_code == 200
    assert "modulos" in resp.json()
