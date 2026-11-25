from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m02_sedes.models import Sedes
from apps.m05_clientes.models import Clientes, Tipos_cliente
from apps.m06_ventas.models import Facturas, Tipos_venta
from apps.m07_domicilios.models import Mensajeros
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


def _client_admin() -> APIClient:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="dom.api@test.local",
        password="Admin#2026demo",
        nombre="Dom",
        apellido="API",
        documento="100009990555",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-dom"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client


@pytest.fixture
def factura_domicilio() -> Facturas:
    sede = Sedes.objects.create(nombre="Sede API", direccion="Calle", estado=True, ciudad="BOG")
    tipo_cli, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"estado": True, "es_tipo_predeterminado": True})
    cliente = Clientes.objects.create(
        nombre="Api",
        apellido="Cliente",
        numero_telefono="+573001112233",
        direccion="Calle 1",
        ciudad="Bogota",
        documento="909091",
        id_tipo_cliente=tipo_cli,
        estado=True,
    )
    tipo_dom, _ = Tipos_venta.objects.get_or_create(nombre="Domicilio", defaults={"estado": True})
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.filter(email="dom.api@test.local").first()
    if not user:
        user = Usuarios.objects.create_user(
            email="dom.api2@test.local",
            password="Admin#2026demo",
            nombre="Dom",
            apellido="API",
            documento="100009990556",
            id_rol=rol,
        )
    return Facturas.objects.create(
        id_sede=sede,
        serie="API",
        numero_factura="8001",
        id_cliente=cliente,
        id_usuario=user,
        id_tipo_venta=tipo_dom,
        subtotal=Decimal("10000"),
        total=Decimal("10000"),
        estado="EMITIDA",
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_api_domicilios_flujo(factura_domicilio: Facturas) -> None:
    client = _client_admin()
    assert client.get("/api/v1/domicilios/bandeja/?vista=activos").status_code == 200
    assert client.get("/api/v1/domicilios/mensajeros/activos/").status_code == 200
    creado = client.post(
        "/api/v1/domicilios/",
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Calle 9",
            "telefono_contacto": "+57300",
            "valor_cobrado_cliente": "3000",
            "valor_pagado_mensajero": "1000",
        },
        format="json",
    )
    assert creado.status_code in (200, 201)
    id_entrega = creado.json()["item"]["id_entrega"]
    m = Mensajeros.objects.create(
        nombre="Api",
        apellido="Mens",
        documento="M-API",
        telefono="3009998877",
        fecha_inicio=timezone.localdate(),
        estado=True,
    )
    assert client.post(
        f"/api/v1/domicilios/{id_entrega}/asignar/",
        {"id_mensajero": m.id_mensajero},
        format="json",
    ).status_code == 200
    assert client.post(
        f"/api/v1/domicilios/{id_entrega}/estado/",
        {"estado": "EN_CAMINO"},
        format="json",
    ).status_code == 200
    assert client.get(f"/api/v1/domicilios/{id_entrega}/").status_code == 200
    assert client.get(f"/api/v1/domicilios/factura/{factura_domicilio.id_factura}/precarga/").status_code == 400
    assert client.get("/api/v1/domicilios/historial/").status_code == 200
    mc = client.post(
        "/api/v1/domicilios/mensajeros/",
        {
            "nombre": "Nuevo",
            "apellido": "Mens",
            "documento": "M-NEW",
            "telefono": "3001234567",
            "fecha_inicio": timezone.localdate().isoformat(),
        },
        format="json",
    )
    assert mc.status_code in (200, 201)
    mid = mc.json()["item"]["id_mensajero"]
    assert client.get("/api/v1/domicilios/mensajeros/").status_code == 200
    assert client.patch(
        f"/api/v1/domicilios/mensajeros/{mid}/",
        {
            "nombre": "Nuevo",
            "apellido": "Mens",
            "documento": "M-NEW",
            "telefono": "3001234567",
            "fecha_inicio": timezone.localdate().isoformat(),
            "version_fila": 1,
        },
        format="json",
    ).status_code == 200
