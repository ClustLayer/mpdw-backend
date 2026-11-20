"""Vistas REST del catálogo (HU 22–30)."""

from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m03_catalogo.models import Categorias_producto, Marcas, Tipos_producto
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


def _cliente() -> APIClient:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="cat.admin@test.local",
        password="Admin#2026demo",
        nombre="Cat",
        apellido="Admin",
        documento="100009990199",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-cat"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client


@pytest.mark.unit
@pytest.mark.django_db
def test_flujo_producto_api(db):
    client = _cliente()
    cat = Categorias_producto.objects.create(nombre="Lacas")
    marca = Marcas.objects.create(nombre="Diana")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    payload = {
        "codigo_producto": "LAC-1",
        "nombre": "Laca",
        "id_categoria": cat.id_categoria,
        "id_marca": marca.id_marca,
        "id_tipo_producto": tipo.id_tipo_producto,
        "unidad_medida": "LT",
        "precio_compra": "5",
        "precio_venta": "9",
        "iva_porcentaje": "19",
        "stock_minimo": 1,
        "inventario_habilitado": False,
    }
    creado = client.post("/api/v1/catalogo/productos/", payload, format="json")
    assert creado.status_code == 201
    pid = creado.json()["producto"]["id_producto"]
    assert client.get("/api/v1/catalogo/productos/?q=Laca").status_code == 200
    edit = client.patch(
        f"/api/v1/catalogo/productos/{pid}/",
        {**payload, "nombre": "Laca mate", "version_fila": creado.json()["producto"]["version_fila"]},
        format="json",
    )
    assert edit.status_code == 200
    assert client.post(f"/api/v1/catalogo/productos/{pid}/estado/", {"activo": False}, format="json").status_code == 200
    assert client.get(f"/api/v1/catalogo/productos/{pid}/historial/").status_code == 200
    params = client.post("/api/v1/catalogo/parametros/marcas/", {"nombre": "Marca nueva"}, format="json")
    assert params.status_code == 201
    assert client.get("/api/v1/catalogo/parametros/marcas/").status_code == 200
    vacio = client.get("/api/v1/catalogo/productos/exportar/?formato=csv&q=no-existe-xyz")
    assert vacio.status_code == 400
    ok = client.get("/api/v1/catalogo/productos/exportar/?formato=csv&estado=inactivo")
    assert ok.status_code == 200
    assert client.get("/api/v1/catalogo/productos/plantilla/").status_code == 200
    assert client.get("/api/v1/catalogo/media/no-existe.webp/").status_code == 404
    assert client.get("/api/v1/catalogo/productos/?page=xx").status_code == 400
    assert client.get("/api/v1/catalogo/productos/999999/").status_code == 404
    assert client.patch("/api/v1/catalogo/productos/999999/", {"codigo_producto": "X"}, format="json").status_code in {400, 404}
    assert client.post("/api/v1/catalogo/productos/999999/estado/", {"activo": True}, format="json").status_code == 404
    assert client.get("/api/v1/catalogo/productos/999999/historial/").status_code == 404
    assert client.get(f"/api/v1/catalogo/productos/{pid}/historial/?desde=2026-12-01&hasta=2026-01-01").status_code == 400
    assert client.post(f"/api/v1/catalogo/productos/{pid}/imagen/", {}, format="multipart").status_code == 400
    assert client.get("/api/v1/catalogo/parametros/nope/").status_code == 400
    assert client.post("/api/v1/catalogo/parametros/nope/", {"nombre": "X"}, format="json").status_code == 400
    assert client.post("/api/v1/catalogo/productos/importar/", {}, format="multipart").status_code == 400
    assert client.get("/api/v1/catalogo/productos/exportar/?formato=pdf").status_code == 400
    conflicto = client.patch(
        f"/api/v1/catalogo/productos/{pid}/",
        {**payload, "version_fila": 1, "nombre": "Otra vez"},
        format="json",
    )
    assert conflicto.status_code in {200, 409}
    from django.core.files.uploadedfile import SimpleUploadedFile

    malo = SimpleUploadedFile("a.txt", b"no", content_type="text/plain")
    assert client.post(f"/api/v1/catalogo/productos/{pid}/imagen/", {"imagen": malo}, format="multipart").status_code == 400
