"""API REST tienda pública (Épica 16)."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Productos, Tipos_producto


@pytest.mark.unit
@pytest.mark.django_db
def test_tienda_api_flujo(db):
    client = APIClient()
    assert client.get("/api/v1/tienda/filtros/").status_code == 200
    sede = Sedes.objects.create(nombre="Sede WA", direccion="Calle 2", estado=True, whatsapp="+573001112233")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="API-1",
        nombre="Brocha",
        precio_venta=Decimal("8000"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    lista = client.get("/api/v1/tienda/catalogo/?q=Brocha")
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1
    slug = f"{p.id_producto}-brocha"
    det = client.get(f"/api/v1/tienda/productos/{slug}/")
    assert det.status_code == 200
    val = client.post(
        "/api/v1/tienda/carrito/validar/",
        {"id_sede": sede.id_sede, "items": [{"id_producto": p.id_producto, "cantidad": 1}]},
        format="json",
    )
    assert val.status_code == 200
    sedes = client.get("/api/v1/tienda/sedes/")
    assert sedes.status_code == 200
    assert any(s["id_sede"] == sede.id_sede for s in sedes.json()["items"])
    wa = client.post("/api/v1/tienda/whatsapp/contacto/", {"id_sede": sede.id_sede}, format="json")
    assert wa.status_code == 200
    assert "url_whatsapp" in wa.json()
    bad = client.get("/api/v1/tienda/catalogo/?precio_min=50&precio_max=10")
    assert bad.status_code == 400
    miss = client.get("/api/v1/tienda/productos/999999-nada/")
    assert miss.status_code == 404
    pedido = client.post(
        "/api/v1/tienda/pedidos/preparar/",
        {
            "cliente_nombre": "Cliente Demo",
            "cliente_telefono": "+573009998877",
            "id_sede": sede.id_sede,
            "items": [{"id_producto": p.id_producto, "cantidad": 1}],
            "clave_idempotencia": "pytest-epic16-1",
        },
        format="json",
    )
    assert pedido.status_code == 201
    assert "url_whatsapp" in pedido.json()


@pytest.mark.unit
@pytest.mark.django_db
def test_tienda_fallas_503(db):
    client = APIClient()
    with patch("apps.m12_tienda_publica.views.TiendaCatalogoService") as mock_cat:
        mock_cat.return_value.listar.side_effect = RuntimeError("fallo")
        assert client.get("/api/v1/tienda/catalogo/").status_code == 503
    with patch("apps.m12_tienda_publica.views.TiendaCatalogoService") as mock_cat:
        mock_cat.return_value.detalle.side_effect = RuntimeError("fallo")
        assert client.get("/api/v1/tienda/productos/1-x/").status_code == 503
    with patch("apps.m12_tienda_publica.views.TiendaPedidoService") as mock_ped:
        mock_ped.return_value.validar_carrito.side_effect = RuntimeError("fallo")
        assert client.post("/api/v1/tienda/carrito/validar/", {"items": []}, format="json").status_code == 503
    with patch("apps.m12_tienda_publica.views.TiendaPedidoService") as mock_ped:
        mock_ped.return_value.contacto_whatsapp.side_effect = RuntimeError("fallo")
        assert client.post("/api/v1/tienda/whatsapp/contacto/", {}, format="json").status_code == 503
    with patch("apps.m12_tienda_publica.views.TiendaPedidoService") as mock_ped:
        mock_ped.return_value.preparar_pedido.side_effect = RuntimeError("fallo")
        assert client.post("/api/v1/tienda/pedidos/preparar/", {}, format="json").status_code == 503
