"""Pruebas de vistas REST Epic 3 (JWT + auth_context)."""

from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Permisos, Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


def _cliente_admin(db) -> APIClient:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="views.admin@test.local",
        password="Admin#2026demo",
        nombre="V",
        apellido="A",
        documento="100009990123",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email,
        "Admin#2026demo",
        "127.0.0.1",
        "pytest",
        "corr-views",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client


@pytest.mark.unit
@pytest.mark.django_db
def test_vistas_roles_crud(db):
    client = _cliente_admin(db)
    assert client.get("/api/v1/roles-permisos/roles").status_code == 200
    c = client.post("/api/v1/roles-permisos/roles", {"nombre": "VistaRol"}, format="json")
    assert c.status_code == 201
    id_rol = c.json()["id_rol"]
    assert client.get(f"/api/v1/roles-permisos/roles/{id_rol}").status_code == 200
    v = c.json()["version_fila"]
    p = client.patch(
        f"/api/v1/roles-permisos/roles/{id_rol}",
        {"descripcion": "Ok", "version_fila": v},
        format="json",
    )
    assert p.status_code == 200
    d = client.delete(f"/api/v1/roles-permisos/roles/{id_rol}")
    assert d.status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_vistas_permisos_y_catalogos(db):
    client = _cliente_admin(db)
    assert client.get("/api/v1/roles-permisos/permisos/catalogos").status_code == 200
    r = client.post(
        "/api/v1/roles-permisos/permisos",
        {"nombre": "P Vista", "modulo": "auditoria", "accion": "Consultar"},
        format="json",
    )
    assert r.status_code == 201
    assert client.get("/api/v1/roles-permisos/permisos?modulo=auditoria").status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_vistas_matriz_y_catalogos_activos(db):
    client = _cliente_admin(db)
    rol = Roles.objects.get(nombre="Administrador")
    assert client.get("/api/v1/roles-permisos/roles/catalogo/activos").status_code == 200
    assert client.get("/api/v1/roles-permisos/usuarios-activos").status_code == 200
    m = client.get(f"/api/v1/roles-permisos/matriz?tipo=rol&id_destino={rol.id_rol}")
    assert m.status_code == 200
    assert client.get("/api/v1/auth/accesos-panel").status_code == 200
    put = client.put(
        "/api/v1/roles-permisos/matriz",
        {"tipo": "rol", "id_destino": rol.id_rol, "cambios": []},
        format="json",
    )
    assert put.status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_vista_validacion_y_permisos_patch(db):
    client = _cliente_admin(db)
    bad = client.post("/api/v1/roles-permisos/roles", {"nombre": ""}, format="json")
    assert bad.status_code == 400
    assert client.post(
        "/api/v1/roles-permisos/permisos",
        {"nombre": "PatchMe", "modulo": "sedes", "accion": "Consultar"},
        format="json",
    ).status_code == 201
    pid = Permisos.objects.get(modulo="sedes", accion="Consultar", nombre="PatchMe").id_permiso
    p = Permisos.objects.get(pk=pid)
    resp = client.patch(
        f"/api/v1/roles-permisos/permisos/{pid}",
        {"descripcion": "Desc", "version_fila": p.version_fila},
        format="json",
    )
    assert resp.status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_vista_rol_no_encontrado(db):
    client = _cliente_admin(db)
    assert client.get("/api/v1/roles-permisos/roles/999999").status_code == 404
    assert client.patch("/api/v1/roles-permisos/roles/999999", {"version_fila": 1}, format="json").status_code == 404
    assert client.delete("/api/v1/roles-permisos/roles/999999").status_code == 404


@pytest.mark.unit
@pytest.mark.django_db
def test_vista_delete_rol_base_protegido(db):
    client = _cliente_admin(db)
    admin = Roles.objects.get(nombre="Administrador")
    resp = client.delete(f"/api/v1/roles-permisos/roles/{admin.id_rol}")
    assert resp.status_code in (400, 403)
    assert resp.status_code != 200
