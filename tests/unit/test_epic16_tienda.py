"""Servicios tienda pública (Épica 16)."""

from decimal import Decimal

import pytest

from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import (
    Categorias_producto,
    Colores_catalogo,
    Marcas,
    Productos,
    Tipos_producto,
)
from apps.m04_inventario.models import Inventarios
from apps.m12_tienda_publica import mensajes as msg
from apps.m12_tienda_publica.slug_util import parse_id_producto, ruta_producto, slugify_nombre
from apps.m12_tienda_publica.tienda_catalogo_service import TiendaCatalogoService
from apps.m12_tienda_publica.tienda_pedido_service import (
    TiendaPedidoService,
    formatear_texto_pedido_whatsapp,
)
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


@pytest.mark.unit
def test_telefono_legible_corto():
    from apps.m12_tienda_publica.tienda_pedido_service import _telefono_legible

    assert _telefono_legible("+12345678") == "+12345678"


def test_formato_pedido_sin_direccion():
    texto = formatear_texto_pedido_whatsapp(
        "Cali",
        "Cliente",
        "+573001112233",
        "",
        "",
        [{"cantidad": 1, "nombre": "P", "codigo_producto": "C1", "subtotal": "1000"}],
        Decimal("1000"),
    )
    assert "Dirección:" not in texto
    assert "Observaciones: Ninguna" in texto


def test_formato_pedido_whatsapp():
    from decimal import Decimal

    texto = formatear_texto_pedido_whatsapp(
        "Cali Centro",
        "Adolfo Quiceno",
        "+573186111159",
        "Calle 15",
        "LLeguen",
        [{"cantidad": 2, "nombre": "Vinilo", "codigo_producto": "VIN1", "subtotal": "160000"}],
        Decimal("160000"),
    )
    assert "PEDIDO WEB — CALI CENTRO" in texto
    assert "*TOTAL:" in texto
    assert "Teléfono:" in texto


@pytest.mark.unit
@pytest.mark.django_db
def test_escaparate_crud_minimo(db):
    from apps.m12_tienda_publica.escaparate_service import EscaparateService
    from apps.m12_tienda_publica.models import Escaparate_seccion

    svc = EscaparateService()
    out = svc.crear({"clave": "demo", "frase": "Kicker", "titulo": "Título", "color_acento": "#111"})
    pk = out["escaparate"]["id_escaparate"]
    assert Escaparate_seccion.objects.filter(pk=pk).exists()
    por_clave = {row["clave"]: row for row in svc.listar_admin()["items"]}
    assert por_clave["demo"]["titulo"] == "Título"


@pytest.mark.unit
@pytest.mark.django_db
def test_asignar_productos_escaparate_y_publico(db):
    from apps.m12_tienda_publica.escaparate_service import EscaparateService

    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="ESC-1",
        nombre="En vitrina",
        precio_venta=Decimal("1000"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    svc = EscaparateService()
    pk = svc.crear({"clave": "pub", "frase": "F", "titulo": "T"})["escaparate"]["id_escaparate"]
    svc.asignar_productos(pk, [p.id_producto])
    pub = svc.listar_publico()["items"]
    assert pub and pub[0]["productos"][0]["id_producto"] == p.id_producto


@pytest.mark.unit
@pytest.mark.django_db
def test_catalogo_incluye_colores(db):
    from apps.m03_catalogo.models import Colores_catalogo, Productos_colores

    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    color = Colores_catalogo.objects.create(nombre="TestR", hex="#112233", es_predefinido=True, estado=True)
    p = Productos.objects.create(
        codigo_producto="COL-1",
        nombre="Vinilo demo",
        precio_venta=Decimal("5000"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    Productos_colores.objects.create(id_producto=p, id_color=color)
    item = TiendaCatalogoService().listar(None, None, None, None, None, None, None, 1, 12, None)["items"][0]
    assert item["colores"] == [{"name": "TestR", "hex": "#112233"}]


@pytest.mark.unit
@pytest.mark.django_db
def test_api_escaparates(db):
    from rest_framework.test import APIClient

    from tests.unit.test_epic3_roles_views import _cliente_admin

    assert APIClient().get("/api/v1/tienda/escaparates/").status_code == 200
    admin = _cliente_admin(db)
    assert admin.get("/api/v1/catalogo/escaparates/").status_code == 200
    c = admin.post(
        "/api/v1/catalogo/escaparates/",
        {"clave": "api-test", "frase": "K", "titulo": "API", "color_acento": "#000"},
        format="json",
    )
    assert c.status_code == 201
    pk = c.json()["escaparate"]["id_escaparate"]
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    prod = Productos.objects.create(
        codigo_producto="ESC-API",
        nombre="API",
        precio_venta=Decimal("1"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
    )
    p = admin.patch(f"/api/v1/catalogo/escaparates/{pk}/", {"titulo": "Nuevo", "version_fila": 1}, format="json")
    assert p.status_code == 200
    a = admin.post(f"/api/v1/catalogo/escaparates/{pk}/productos/", {"ids_producto": [prod.id_producto]}, format="json")
    assert a.status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_delete_imagen_producto_api(db):
    from tests.unit.test_epic3_roles_views import _cliente_admin

    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    p = Productos.objects.create(
        codigo_producto="IMG-DEL",
        nombre="Con foto",
        precio_venta=Decimal("1"),
        inventario_habilitado=False,
        estado=True,
        id_tipo_producto=tipo,
        imagen_url="productos/t.webp",
    )
    admin = _cliente_admin(db)
    r = admin.delete(f"/api/v1/catalogo/productos/{p.id_producto}/imagen/")
    assert r.status_code == 200
    p.refresh_from_db()
    assert p.imagen_url == ""


@pytest.mark.unit
@pytest.mark.django_db
def test_escaparate_actualizar_conflict(db):
    from apps.m12_tienda_publica.escaparate_service import EscaparateService

    svc = EscaparateService()
    pk = svc.crear({"clave": "conf", "frase": "F", "titulo": "T"})["escaparate"]["id_escaparate"]
    svc.actualizar(pk, {"titulo": "T2", "version_fila": 1})
    with pytest.raises(ReglaNegocioError) as exc:
        svc.actualizar(pk, {"titulo": "T3", "version_fila": 1})
    assert exc.value.codigo == "CONFLICTO"


@pytest.mark.unit
@pytest.mark.django_db
def test_escaparate_dup_clave(db):
    from apps.m12_tienda_publica.escaparate_service import EscaparateService

    svc = EscaparateService()
    svc.crear({"clave": "dup", "frase": "A", "titulo": "A"})
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear({"clave": "dup", "frase": "B", "titulo": "B"})
    assert exc.value.codigo == "DUPLICADO"


@pytest.mark.unit
@pytest.mark.django_db
def test_api_colores_producto(db):
    from tests.unit.test_epic3_roles_views import _cliente_admin

    admin = _cliente_admin(db)
    assert admin.get("/api/v1/catalogo/colores/").status_code == 200
    c = admin.post("/api/v1/catalogo/colores/", {"nombre": "Azul cielo", "hex": "#AABBCC"}, format="json")
    assert c.status_code == 201
    id_color = c.json()["color"]["id_color"]
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True, "estado": True})
    cat = Categorias_producto.objects.filter(estado=True).first()
    marca = Marcas.objects.filter(estado=True).first()
    if not cat:
        cat = Categorias_producto.objects.create(nombre="Cat", estado=True)
    if not marca:
        marca = Marcas.objects.create(nombre="Mar", estado=True)
    body = {
        "codigo_producto": "CLR-1",
        "nombre": "Vinilo color",
        "id_categoria": cat.id_categoria,
        "id_marca": marca.id_marca,
        "id_tipo_producto": tipo.id_tipo_producto,
        "unidad_medida": "UND",
        "precio_compra": "1000",
        "precio_venta": "2000",
        "iva_porcentaje": "19",
        "stock_minimo": 0,
        "ids_colores": [id_color],
    }
    r = admin.post("/api/v1/catalogo/productos/", body, format="json")
    assert r.status_code == 201
    pid = r.json()["producto"]["id_producto"]
    d = admin.get(f"/api/v1/catalogo/productos/{pid}/")
    assert d.status_code == 200
    assert d.json()["ids_colores"] == [id_color]
    pre = Colores_catalogo.objects.filter(es_predefinido=True).first()
    if pre:
        p2 = admin.patch(f"/api/v1/catalogo/productos/{pid}/", {"version_fila": 1, **body, "ids_colores": [id_color, pre.id_color]}, format="json")
        assert p2.status_code == 200
        assert len(p2.json()["producto"]["ids_colores"]) == 2
        p3 = admin.patch(f"/api/v1/catalogo/productos/{pid}/", {"version_fila": 2, **body, "ids_colores": []}, format="json")
        assert p3.status_code == 200
        assert p3.json()["producto"]["ids_colores"] == []


@pytest.mark.unit
@pytest.mark.django_db
def test_api_colores_hex_invalido(db):
    from tests.unit.test_epic3_roles_views import _cliente_admin

    admin = _cliente_admin(db)
    r = admin.post("/api/v1/catalogo/colores/", {"nombre": "Mal", "hex": "rojo"}, format="json")
    assert r.status_code == 400
    ok = admin.post("/api/v1/catalogo/colores/", {"nombre": "Índigo", "hex": "#334455"}, format="json")
    assert ok.status_code == 201
    id1 = ok.json()["color"]["id_color"]
    dup = admin.post("/api/v1/catalogo/colores/", {"nombre": "Índigo", "hex": "#334455"}, format="json")
    assert dup.status_code == 201
    assert dup.json()["color"]["id_color"] == id1
    clash = admin.post("/api/v1/catalogo/colores/", {"nombre": "Índigo", "hex": "#111111"}, format="json")
    assert clash.status_code == 400
