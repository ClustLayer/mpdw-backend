from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m02_sedes.models import Sedes
from apps.m06_ventas.models import Facturas, Facturas_electronicas, Tipos_venta
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


@pytest.fixture
def api_client() -> APIClient:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="fe.api@test.local",
        password="Admin#2026demo",
        nombre="Fe",
        apellido="API",
        documento="100009990411",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-fe"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client


@pytest.fixture
def id_fe() -> int:
    sede = Sedes.objects.create(nombre="Sede API FE", direccion="Calle", estado=True, ciudad="BOG")
    tipo, _ = Tipos_venta.objects.get_or_create(nombre="Mostrador", defaults={"estado": True})
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.filter(email="fe.api@test.local").first()
    if not user:
        user = Usuarios.objects.create_user(
            email="fe.api2@test.local",
            password="Admin#2026demo",
            nombre="Fe",
            apellido="API",
            documento="100009990412",
            id_rol=rol,
        )
    f = Facturas.objects.create(
        id_sede=sede,
        serie="API",
        numero_factura="2002",
        id_usuario=user,
        id_tipo_venta=tipo,
        subtotal=Decimal("1"),
        total=Decimal("1"),
        estado="EMITIDA",
        requiere_factura_electronica=True,
    )
    return Facturas_electronicas.objects.create(id_factura=f, estado="PENDIENTE").id_factura_electronica


@pytest.mark.unit
@pytest.mark.django_db
def test_api_facturacion_externa(api_client: APIClient, id_fe: int) -> None:
    assert api_client.get("/api/v1/ventas/facturacion-externa/").status_code == 200
    assert api_client.get(f"/api/v1/ventas/facturacion-externa/{id_fe}/").status_code == 200
    assert api_client.get(f"/api/v1/ventas/facturacion-externa/{id_fe}/soporte/").status_code == 404
    post = api_client.post(
        f"/api/v1/ventas/facturacion-externa/{id_fe}/estado/",
        {
            "estado": "GENERADA_EXTERNA",
            "numero_electronico": "CUDE-123",
            "url_pdf": "https://storage.test/doc.pdf",
            "version_fila": 1,
        },
        format="json",
    )
    assert post.status_code == 200
    assert api_client.get(f"/api/v1/ventas/facturacion-externa/{id_fe}/soporte/").status_code == 200
