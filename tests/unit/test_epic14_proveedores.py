from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from apps.m14_proveedores.admin_proveedores_service import AdminProveedoresService
from apps.m14_proveedores.models import TIPO_DOC_NIT, Proveedores
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    return AuthContext(0, "a@test.local", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1")


@pytest.mark.unit
@pytest.mark.django_db
def test_proveedor_crud(ctx):
    svc = AdminProveedoresService(audit=MagicMock())
    body = {
        "nombre": "Distribuidora ACME",
        "tipo_documento": TIPO_DOC_NIT,
        "numero_documento": "900123456",
        "telefono": "+573001234567",
        "correo": "compras@acme.test",
    }
    out = svc.crear(ctx, body)
    assert "correctamente" in out["mensaje"]
    pk = out["proveedor"]["id_proveedor"]
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {**body, "nombre": "Otro ACME"})
    patch = svc.actualizar(
        ctx,
        pk,
        {**body, "ciudad": "Bogotá", "version_fila": 1, "estado": True},
    )
    assert patch["proveedor"]["ciudad"] == "Bogotá"
    assert svc.activos()["items"]


@pytest.mark.unit
@pytest.mark.django_db
def test_proveedor_validaciones(ctx):
    svc = AdminProveedoresService(audit=MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"nombre": "X", "tipo_documento": TIPO_DOC_NIT, "telefono": "bad"})
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"nombre": "", "tipo_documento": TIPO_DOC_NIT})
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"nombre": "Mail", "tipo_documento": TIPO_DOC_NIT, "correo": "no-es-correo"})
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"nombre": "Tipo", "tipo_documento": "RFC"})


@pytest.mark.unit
@pytest.mark.django_db
def test_api_proveedores():
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="prov.admin@test.local",
        password="Admin#2026demo",
        nombre="Prov",
        apellido="Admin",
        documento="100009990177",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-prov"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/proveedores/").status_code == 200
    r = client.post(
        "/api/v1/proveedores/",
        {"nombre": "Proveedor Demo", "tipo_documento": TIPO_DOC_NIT},
        format="json",
    )
    assert r.status_code == 201
    assert client.get("/api/v1/proveedores/activos/").status_code == 200
    pk = r.json()["proveedor"]["id_proveedor"]
    assert client.get(f"/api/v1/proveedores/{pk}/").status_code == 200
    assert client.patch(
        f"/api/v1/proveedores/{pk}/",
        {"nombre": "Proveedor Demo", "tipo_documento": TIPO_DOC_NIT, "version_fila": 1},
        format="json",
    ).status_code == 200
    assert client.get("/api/v1/proveedores/9999999/").status_code == 404


@pytest.mark.unit
@pytest.mark.django_db
def test_proveedor_no_encontrado(ctx):
    with pytest.raises(ReglaNegocioError) as exc:
        AdminProveedoresService().actualizar(ctx, 999999, {"nombre": "X", "tipo_documento": TIPO_DOC_NIT, "version_fila": 1})
    assert exc.value.codigo == "NO_ENCONTRADO"


@pytest.mark.unit
@pytest.mark.django_db
def test_proveedor_concurrencia(ctx):
    svc = AdminProveedoresService(audit=MagicMock())
    out = svc.crear(ctx, {"nombre": "Beta", "tipo_documento": TIPO_DOC_NIT})
    pk = out["proveedor"]["id_proveedor"]
    with pytest.raises(ReglaNegocioError) as exc:
        svc.actualizar(ctx, pk, {"nombre": "Beta", "tipo_documento": TIPO_DOC_NIT, "version_fila": 99})
    assert exc.value.codigo == "CONCURRENCIA"


@pytest.mark.unit
@pytest.mark.django_db
def test_proveedor_listar(ctx):
    Proveedores.objects.create(nombre="Alpha", tipo_documento=TIPO_DOC_NIT)
    svc = AdminProveedoresService(audit=MagicMock())
    data = svc.listar("Alpha", "activo", 1, 10)
    assert data["items"]
    vacio = svc.listar("zzznomatch", "todos", 1, 10)
    assert vacio["mensaje"]
    assert svc.obtener(Proveedores.objects.get(nombre="Alpha").id_proveedor)["nombre"] == "Alpha"
    assert svc.listar("", "inactivo", 1, 10)["items"] == []
