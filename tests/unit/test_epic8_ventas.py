from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Categorias_producto, Marcas, Productos, Tipos_producto
from apps.m04_inventario.admin_service import AdminInventarioService
from apps.m04_inventario.models import Inventarios
from apps.m06_ventas.admin_ventas_service import AdminVentasService
from apps.m06_ventas.models import Facturas, Metodos_pago, Tipos_venta
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from apps.m14_proveedores.models import TIPO_DOC_NIT, Proveedores
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    return AuthContext(1, "admin@test.local", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1")


def _producto_y_stock() -> tuple[Productos, Sedes, int, int]:
    cat = Categorias_producto.objects.create(nombre="Cat Venta")
    marca = Marcas.objects.create(nombre="Marca Venta")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Producto Terminado", defaults={"es_base": True})
    sede = Sedes.objects.create(nombre="Sede POS", direccion="Calle 10", estado=True, ciudad="CAL")
    prod = Productos.objects.create(
        codigo_producto="POS-001",
        nombre="Esmalte POS",
        id_categoria=cat,
        id_marca=marca,
        id_tipo_producto=tipo,
        precio_venta=Decimal("10000"),
        precio_compra=Decimal("7000"),
        unidad_medida="UND",
        inventario_habilitado=True,
    )
    tipo_venta, _ = Tipos_venta.objects.get_or_create(nombre="Mostrador", defaults={"estado": True})
    ef, _ = Metodos_pago.objects.get_or_create(nombre="Efectivo", defaults={"estado": True})
    tr, _ = Metodos_pago.objects.get_or_create(nombre="Transferencia", defaults={"estado": True})
    prov = Proveedores.objects.create(nombre="Prov Venta", tipo_documento=TIPO_DOC_NIT, estado=True)
    AdminInventarioService().entrada(
        AuthContext(1, "a", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1"),
        {
            "id_producto": prod.id_producto,
            "id_sede": sede.id_sede,
            "cantidad": "20",
            "motivo": "Semilla",
            "id_proveedor": prov.id_proveedor,
            "costo_unitario": "7000",
        },
    )
    return prod, sede, tipo_venta.id_tipo_venta, ef.id_metodo_pago


@pytest.mark.unit
@pytest.mark.django_db
def test_emitir_factura_resta_stock(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    usuario = Usuarios.objects.first()
    if usuario:
        ctx = AuthContext(usuario.id_usuario, usuario.email, "Administrador", (sede.id_sede,), True, id_rol=1, ip="127.0.0.1")
    out = svc.emitir(
        ctx,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 2}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 23800}],
        },
    )
    assert "emitida" in out["mensaje"].lower()
    inv = Inventarios.objects.get(id_producto=prod, id_sede=sede)
    assert inv.cantidad_actual == Decimal("18")
    assert Facturas.objects.filter(estado="EMITIDA").count() == 1


@pytest.mark.unit
@pytest.mark.django_db
def test_stock_insuficiente(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx,
            {
                "id_sede": sede.id_sede,
                "id_tipo_venta": id_tipo,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 50}],
                "pagos": [{"id_metodo_pago": id_ef, "valor": 1000000}],
            },
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_anular_factura(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    out = svc.emitir(
        ctx,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 2}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 23800}],
        },
    )
    pk = out["factura"]["id_factura"]
    msg = svc.anular(ctx, pk, {"motivo": "Error de digitación en caja de prueba"})
    assert "anulada" in msg["mensaje"].lower()
    inv = Inventarios.objects.get(id_producto=prod, id_sede=sede)
    assert inv.cantidad_actual == Decimal("20")


@pytest.mark.unit
@pytest.mark.django_db
def test_api_ventas_pos():
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="pos.admin@test.local",
        password="Admin#2026demo",
        nombre="Pos",
        apellido="Admin",
        documento="100009990199",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-pos"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/ventas/pos/catalogos/").status_code == 200
    _producto_y_stock()
    assert client.get("/api/v1/ventas/facturas/").status_code == 200