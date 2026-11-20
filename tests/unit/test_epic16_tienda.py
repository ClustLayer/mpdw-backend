"""Servicios tienda pública (Épica 16)."""

from decimal import Decimal

import pytest

from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Categorias_producto, Marcas, Productos, Tipos_producto
from apps.m04_inventario.models import Inventarios
from apps.m12_tienda_publica import mensajes as msg
from apps.m12_tienda_publica.slug_util import parse_id_producto, ruta_producto, slugify_nombre
from apps.m12_tienda_publica.tienda_catalogo_service import TiendaCatalogoService
from apps.m12_tienda_publica.tienda_pedido_service import TiendaPedidoService
from contratos.excepciones import ReglaNegocioError


@pytest.mark.unit
def test_slug_util():
    assert slugify_nombre("Pintura Azul #1") == "pintura-azul-1"
    slug = ruta_producto(42, "Laca Mate")
    assert slug.startswith("42-")
    assert parse_id_producto(slug) == 42
    assert parse_id_producto("99") == 99
    assert parse_id_producto("abc") is None


@pytest.mark.unit
@pytest.mark.django_db
def test_catalogo_listar_y_detalle(db):
    cat = Categorias_producto.objects.create(nombre="Esmaltes", estado=True)
    marca = Marcas.objects.create(nombre="Diana", estado=True)
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="T-100",
        nombre="Esmalte Rojo",
        id_categoria=cat,
        id_marca=marca,
        id_tipo_producto=tipo,
        precio_venta=Decimal("12000"),
        inventario_habilitado=False,
        estado=True,
    )
    svc = TiendaCatalogoService()
    data = svc.listar(None, None, None, None, None, None, None, 1, 12, None)
    assert data["total"] == 1
    assert "Mostrando" in data["mensaje"]
    slug = ruta_producto(p.id_producto, p.nombre)
    det = svc.detalle(slug, None)
    assert det["item"]["nombre"] == "Esmalte Rojo"
    assert "seo" in det["item"]
    vacio = svc.listar("no-existe-xyz", None, None, None, None, None, None, 1, 12, None)
    assert vacio["total"] == 0


@pytest.mark.unit
@pytest.mark.django_db
def test_catalogo_precio_rango(db):
    Productos.objects.create(
        codigo_producto="T-2",
        nombre="A",
        precio_venta=Decimal("10"),
        inventario_habilitado=False,
        estado=True,
    )
    with pytest.raises(ReglaNegocioError) as exc:
        TiendaCatalogoService().listar(None, None, None, None, "100", "50", None, 1, 12, None)
    assert exc.value.mensaje == msg.MSG_PRECIO_RANGO


@pytest.mark.unit
@pytest.mark.django_db
def test_stock_agotado(db):
    sede = Sedes.objects.create(nombre="Centro", direccion="Calle 1", estado=True, whatsapp="+573001112233")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="ST-1",
        nombre="Con stock",
        precio_venta=Decimal("5000"),
        inventario_habilitado=True,
        estado=True,
        id_tipo_producto=tipo,
    )
    Inventarios.objects.create(id_producto=p, id_sede=sede, cantidad_actual=Decimal("0"))
    data = TiendaCatalogoService().listar(None, None, None, None, None, None, None, 1, 12, sede.id_sede)
    assert data["items"][0]["agotado"] is True


@pytest.mark.unit
@pytest.mark.django_db
def test_pedido_validar_y_preparar(db):
    sede = Sedes.objects.create(nombre="Centro", direccion="Calle 1", estado=True, whatsapp="+573001112233")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="P-1",
        nombre="Pintura",
        precio_venta=Decimal("10000"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    svc = TiendaPedidoService()
    val = svc.validar_carrito(sede.id_sede, [{"id_producto": p.id_producto, "cantidad": 2}])
    assert val["mensaje"] == msg.MSG_CARRITO_VALIDADO
    assert Decimal(val["total"]) == Decimal("20000")
    out = svc.preparar_pedido(
        {
            "cliente_nombre": "Ana Pérez",
            "cliente_telefono": "+573001234567",
            "id_sede": sede.id_sede,
            "items": [{"id_producto": p.id_producto, "cantidad": 1}],
        }
    )
    assert out["mensaje"] == msg.MSG_PEDIDO_LISTO
    assert out["url_whatsapp"].startswith("https://wa.me/")
    assert len(out["url_whatsapp"]) <= msg.WHATSAPP_URL_MAX


@pytest.mark.unit
@pytest.mark.django_db
def test_pedido_telefono_invalido(db):
    sede = Sedes.objects.create(nombre="Centro", direccion="Calle 1", estado=True, whatsapp="+573001112233")
    with pytest.raises(ReglaNegocioError) as exc:
        TiendaPedidoService().preparar_pedido(
            {"cliente_nombre": "X", "cliente_telefono": "123", "id_sede": sede.id_sede, "items": []}
        )
    assert exc.value.mensaje == msg.MSG_TELEFONO


@pytest.mark.unit
@pytest.mark.django_db
def test_contacto_whatsapp_corporativo(db):
    out = TiendaPedidoService().contacto_whatsapp(None, "Hola")
    assert "wa.me" in out["url_whatsapp"]


@pytest.mark.unit
@pytest.mark.django_db
def test_detalle_inactivo(db):
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="OFF-1",
        nombre="Inactivo",
        precio_venta=Decimal("1"),
        inventario_habilitado=False,
        estado=False,
        id_tipo_producto=tipo,
    )
    with pytest.raises(ReglaNegocioError):
        TiendaCatalogoService().detalle(ruta_producto(p.id_producto, p.nombre), None)


@pytest.mark.unit
@pytest.mark.django_db
def test_preparar_sin_whatsapp_sede(db):
    sede = Sedes.objects.create(nombre="Sin WA", direccion="X", estado=True, whatsapp="")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="W-1",
        nombre="P",
        precio_venta=Decimal("1"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    with pytest.raises(ReglaNegocioError) as exc:
        TiendaPedidoService().preparar_pedido(
            {
                "cliente_nombre": "A",
                "cliente_telefono": "+573001234567",
                "id_sede": sede.id_sede,
                "items": [{"id_producto": p.id_producto, "cantidad": 1}],
            }
        )
    assert exc.value.mensaje == msg.MSG_SEDE_SIN_WHATSAPP


@pytest.mark.unit
@pytest.mark.django_db
def test_validar_precio_cliente_ignorado(db):
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="PC-1",
        nombre="Prod",
        precio_venta=Decimal("5000"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    out = TiendaPedidoService().validar_carrito(
        None,
        [{"id_producto": p.id_producto, "cantidad": 1, "precio_cliente": "1"}],
    )
    assert out["hubo_cambios"] is True
    assert msg.MSG_PRECIO_CAMBIO.split("{")[0] in out["mensaje"]


@pytest.mark.unit
@pytest.mark.django_db
def test_validar_carrito_vacio(db):
    with pytest.raises(ReglaNegocioError):
        TiendaPedidoService().validar_carrito(None, [])


@pytest.mark.unit
@pytest.mark.django_db
def test_catalogo_filtros_y_orden(db):
    cat = Categorias_producto.objects.create(nombre="Cat", estado=True)
    marca = Marcas.objects.create(nombre="M", estado=True)
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="TipoX", defaults={"es_base": True, "estado": True})
    Productos.objects.create(
        codigo_producto="ORD-1",
        nombre="Zeta",
        precio_venta=Decimal("100"),
        inventario_habilitado=False,
        estado=True,
        id_categoria=cat,
        id_marca=marca,
        id_tipo_producto=tipo,
    )
    svc = TiendaCatalogoService()
    assert svc.filtros()["categorias"]
    data = svc.listar(None, cat.id_categoria, marca.id_marca, tipo.id_tipo_producto, None, None, "nombre_desc", 1, 12, None)
    assert data["total"] == 1
    data2 = svc.listar("Zeta", None, None, None, "50", "200", "precio_desc", 1, 12, None)
    assert data2["total"] == 1


@pytest.mark.unit
@pytest.mark.django_db
def test_pedido_idempotencia(db):
    sede = Sedes.objects.create(nombre="Centro", direccion="Calle 1", estado=True, whatsapp="+573001112233")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="IDEM-1",
        nombre="X",
        precio_venta=Decimal("1000"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    payload = {
        "cliente_nombre": "B",
        "cliente_telefono": "+573001234567",
        "id_sede": sede.id_sede,
        "items": [{"id_producto": p.id_producto, "cantidad": 1}],
        "clave_idempotencia": "clave-unica-ep16",
    }
    svc = TiendaPedidoService()
    a = svc.preparar_pedido(payload)
    b = svc.preparar_pedido(payload)
    assert a["id_pedido_web"] == b["id_pedido_web"]


@pytest.mark.unit
@pytest.mark.django_db
def test_catalogo_precio_invalido(db):
    with pytest.raises(ReglaNegocioError):
        TiendaCatalogoService().listar(None, None, None, None, "no-num", None, None, 1, 12, None)


@pytest.mark.unit
@pytest.mark.django_db
def test_validar_cantidad_invalida(db):
    with pytest.raises(ReglaNegocioError) as exc:
        TiendaPedidoService().validar_carrito(None, [{"id_producto": 1, "cantidad": 0}])
    assert exc.value.mensaje == msg.MSG_CANTIDAD


@pytest.mark.unit
def test_parse_id_producto_vacio():
    assert parse_id_producto("") is None
    assert parse_id_producto("  ") is None


@pytest.mark.unit
@pytest.mark.django_db
def test_contacto_url_demasiado_larga(db):
    with pytest.raises(ReglaNegocioError) as exc:
        TiendaPedidoService().contacto_whatsapp(None, "x" * 2500)
    assert exc.value.codigo == "URL_LARGA"


@pytest.mark.unit
@pytest.mark.django_db
def test_validar_tope_99_unidades(db):
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="MAX-1",
        nombre="Bulk",
        precio_venta=Decimal("10"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    out = TiendaPedidoService().validar_carrito(None, [{"id_producto": p.id_producto, "cantidad": 120}])
    assert out["hubo_cambios"] is True
    assert out["items"][0]["cantidad"] == 99
