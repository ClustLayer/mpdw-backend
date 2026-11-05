"""Integracion API Epic 2 - administracion de usuarios."""

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes


@pytest.fixture
def admin_user(db):
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    return Usuarios.objects.create_user(
        email="admin.api@test.local",
        password="Admin#2026demo",
        nombre="Admin",
        apellido="API",
        documento="100006789012",
        id_rol=rol,
    )


@pytest.fixture
def sede(db):
    return Sedes.objects.create(nombre="Sede API", direccion="Calle 2", ciudad="Cali", estado=True)


@pytest.mark.integration
@pytest.mark.django_db
def test_listar_usuarios_como_admin(admin_user, sede):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.get("/api/v1/usuarios/?page=1")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["total"] >= 1


@pytest.mark.integration
@pytest.mark.django_db
def test_crear_usuario_via_api(admin_user, sede):
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.post(
        "/api/v1/usuarios/",
        {
            "nombre": "Api",
            "apellido": "Nuevo",
            "documento": "100007890123",
            "telefono": "3001112233",
            "email": "api.nuevo@test.local",
            "id_rol": rol.id_rol,
            "sedes": [{"id_sede": sede.id_sede, "es_principal": True}],
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["mensaje"]
