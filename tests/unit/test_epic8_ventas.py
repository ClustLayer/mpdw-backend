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
from apps.m05_clientes.models import Clientes, Tipos_cliente
from apps.m06_ventas.admin_ventas_service import AdminVentasService
from apps.m06_ventas.models import Facturas, Metodos_pago, Tipos_venta
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from apps.m14_proveedores.models import TIPO_DOC_NIT, Proveedores
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    rol, _ = Roles.objects.get_or_create(
        nombre="Administrador", defaults={"es_rol_base": True, "estado": True}
    )
    user = Usuarios.objects.create_user(
        email="ventas.epic8@test.local",
        password="Admin#2026demo",
        nombre="Ventas",
        apellido="Epic8",
        documento="100009990288",
        id_rol=rol,
    )
    return AuthContext(
        user.id_usuario,
        user.email,
        "Administrador",
        (),
        True,
        id_rol=rol.id_rol,
        ip="127.0.0.1",
    )


def _ctx_sede(ctx: AuthContext, sede: Sedes) -> AuthContext:
    return AuthContext(
        ctx.id_usuario,
        ctx.email,
        ctx.rol_nombre,
        (sede.id_sede,),
        ctx.es_global,
        id_rol=ctx.id_rol,
        ip=ctx.ip,
    )


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
    rol, _ = Roles.objects.get_or_create(
        nombre="Administrador", defaults={"es_rol_base": True, "estado": True}
    )
    op = Usuarios.objects.filter(email="ventas.epic8@test.local").first()
    if not op:
        op = Usuarios.objects.create_user(
            email="inventario.epic8@test.local",
            password="Admin#2026demo",
            nombre="Inv",
            apellido="Epic8",
            documento="100009990289",
            id_rol=rol,
        )
    AdminInventarioService().entrada(
        AuthContext(op.id_usuario, op.email, "Administrador", (sede.id_sede,), True, id_rol=rol.id_rol, ip="127.0.0.1"),
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
    ctx_sede = _ctx_sede(ctx, sede)
    out = svc.emitir(
        ctx_sede,
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
    ctx_sede = _ctx_sede(ctx, sede)
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
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
    ctx_sede = _ctx_sede(ctx, sede)
    out = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 2}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 23800}],
        },
    )
    pk = out["factura"]["id_factura"]
    msg = svc.anular(ctx_sede, pk, {"motivo": "Error de digitación en caja de prueba"})
    assert "anulada" in msg["mensaje"].lower()
    inv = Inventarios.objects.get(id_producto=prod, id_sede=sede)
    assert inv.cantidad_actual == Decimal("20")


@pytest.mark.unit
@pytest.mark.django_db
def test_catalogos_listar_detalle_y_devolucion(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    assert svc.catalogos_pos()["metodos_pago"]
    busqueda = svc.buscar_productos("POS", sede.id_sede)
    assert busqueda["items"]
    out = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "requiere_factura_electronica": True,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 2}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 23800}],
        },
    )
    pk = out["factura"]["id_factura"]
    lista = svc.listar(ctx_sede, {"q": out["factura"]["consecutivo"][:4]}, 1, 15)
    assert lista["total"] >= 1
    det = svc.obtener(ctx_sede, pk)
    assert det["factura"]["lineas"]
    svc.devolucion(
        ctx_sede,
        pk,
        {
            "motivo": "Cliente devolvió un bote sin abrir",
            "lineas": [{"id_detalle": det["factura"]["lineas"][0]["id_detalle"], "cantidad": 1}],
        },
    )
    inv = Inventarios.objects.get(id_producto=prod, id_sede=sede)
    assert inv.cantidad_actual == Decimal("19")


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_filtros_y_anular_validaciones(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    emit = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
        },
    )
    pk = emit["factura"]["id_factura"]
    lista = svc.listar(
        ctx_sede,
        {
            "estado": "EMITIDA",
            "id_sede": str(sede.id_sede),
            "id_tipo_venta": str(id_tipo),
            "id_usuario": str(ctx_sede.id_usuario),
            "margen_negativo": "0",
        },
        1,
        10,
    )
    assert lista["items"]
    Facturas.objects.filter(pk=pk).update(margen_negativo=True)
    assert svc.listar(ctx_sede, {"margen_negativo": "1"}, 1, 10)["total"] >= 1
    svc.anular(ctx_sede, pk, {"motivo": "Error de digitación en caja de prueba"})
    with pytest.raises(ReglaNegocioError):
        svc.anular(ctx_sede, pk, {"motivo": "Error de digitación en caja de prueba"})
    with pytest.raises(ReglaNegocioError):
        svc.obtener(ctx_sede, 999_999)


@pytest.mark.unit
@pytest.mark.django_db
def test_devolucion_validaciones(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    det = svc.obtener(
        ctx_sede,
        svc.emitir(
            ctx_sede,
            {
                "id_sede": sede.id_sede,
                "id_tipo_venta": id_tipo,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 2}],
                "pagos": [{"id_metodo_pago": id_ef, "valor": 23800}],
            },
        )["factura"]["id_factura"],
    )["factura"]
    pk = det["id_factura"]
    id_det = det["lineas"][0]["id_detalle"]
    with pytest.raises(ReglaNegocioError):
        svc.devolucion(ctx_sede, pk, {"motivo": "", "lineas": [{"id_detalle": id_det, "cantidad": 1}]})
    with pytest.raises(ReglaNegocioError):
        svc.devolucion(
            ctx_sede,
            pk,
            {"motivo": "Devolución excesiva", "lineas": [{"id_detalle": id_det, "cantidad": 99}]},
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_devolucion_sin_lineas(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    pk = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
        },
    )["factura"]["id_factura"]
    with pytest.raises(ReglaNegocioError):
        svc.devolucion(ctx_sede, pk, {"motivo": "Sin productos", "lineas": []})


@pytest.mark.unit
@pytest.mark.django_db
def test_buscar_productos_sin_coincidencias(ctx):
    _, sede, _, _ = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    out = svc.buscar_productos("zzz-sin-stock", sede.id_sede)
    assert out["items"] == []
    lista = svc.buscar_productos("", sede.id_sede)
    assert lista["items"]
    assert "Mostrando" in lista["mensaje"]


@pytest.mark.unit
@pytest.mark.django_db
def test_emitir_con_cliente(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    tipo_cli, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"estado": True})
    cliente = Clientes.objects.create(
        nombre="María",
        numero_telefono="+573001112233",
        id_tipo_cliente=tipo_cli,
        estado=True,
    )
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    out = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "id_cliente": cliente.id_cliente,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
        },
    )
    assert out["factura"]["id_cliente"] == cliente.id_cliente


@pytest.mark.unit
@pytest.mark.django_db
def test_anular_motivo_corto(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    pk = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
        },
    )["factura"]["id_factura"]
    with pytest.raises(ReglaNegocioError):
        svc.anular(ctx_sede, pk, {"motivo": "corto"})


@pytest.mark.unit
@pytest.mark.django_db
def test_clave_idempotencia_emision(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    body = {
        "id_sede": sede.id_sede,
        "id_tipo_venta": id_tipo,
        "clave_idempotencia": "idem-epic8-unit",
        "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
        "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
    }
    first = svc.emitir(ctx_sede, body)
    second = svc.emitir(ctx_sede, body)
    assert first["factura"]["id_factura"] == second["factura"]["id_factura"]


@pytest.mark.unit
@pytest.mark.django_db
def test_emitir_validaciones_varias(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    base = {"id_sede": sede.id_sede, "id_tipo_venta": id_tipo}
    with pytest.raises(ReglaNegocioError):
        svc.emitir(ctx_sede, {**base, "lineas": [], "pagos": [{"id_metodo_pago": id_ef, "valor": 1}]})
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
            {
                **base,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 0}],
                "pagos": [{"id_metodo_pago": id_ef, "valor": 1}],
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
            {
                **base,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
                "comprador_correo": "correo-invalido",
                "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
            {
                **base,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
                "descuento_general": {"tipo_descuento": "PORCENTAJE", "porcentaje": 5},
                "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
            {
                **base,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
                "pagos": [{"id_metodo_pago": id_ef, "valor": 1}],
            },
        )


@pytest.mark.unit
def test_validar_autorizacion_sin_credenciales():
    svc = AdminVentasService(audit=MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc._validar_autorizacion({})


@pytest.mark.unit
@pytest.mark.django_db
def test_editar_emitida_y_transferencia_exceso(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    tr = Metodos_pago.objects.get(nombre="Transferencia")
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    pk = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
        },
    )["factura"]["id_factura"]
    with pytest.raises(ReglaNegocioError):
        svc.editar(ctx_sede, pk, {"version_fila": 1, "observaciones": "n/a"})
    with pytest.raises(ReglaNegocioError):
        svc._validar_pagos(
            [{"id_metodo_pago": tr.id_metodo_pago, "valor": 50000, "referencia": "TR-1"}],
            Decimal("11900"),
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_pago_transferencia_sin_referencia(ctx):
    prod, sede, id_tipo, _ef = _producto_y_stock()
    tr = Metodos_pago.objects.get(nombre="Transferencia")
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
            {
                "id_sede": sede.id_sede,
                "id_tipo_venta": id_tipo,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
                "pagos": [{"id_metodo_pago": tr.id_metodo_pago, "valor": 11900}],
            },
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_editar_observaciones_factura_emitida(ctx):
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    id_met = id_ef
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    svc._asegurar_jornada(ctx_sede, sede.id_sede)
    f = Facturas.objects.create(
        id_sede_id=sede.id_sede,
        serie="POS-TEST",
        numero_factura="0000000001",
        id_usuario_id=ctx_sede.id_usuario,
        id_tipo_venta_id=id_tipo,
        subtotal=Decimal("100"),
        descuento=Decimal("0"),
        impuesto=Decimal("0"),
        total=Decimal("100"),
        estado="BORRADOR",
    )
    out = svc.editar(
        ctx_sede,
        f.id_factura,
        {"version_fila": 1, "observaciones": "Corrección menor en notas"},
    )
    assert "actualizada" in out["mensaje"].lower()
    f.refresh_from_db()
    svc.editar(
        ctx_sede,
        f.id_factura,
        {
            "version_fila": f.version_fila,
            "pagos": [{"id_metodo_pago": id_met, "valor": 100}],
        },
    )
    with pytest.raises(ReglaNegocioError) as exc:
        svc.editar(ctx_sede, f.id_factura, {"version_fila": 0, "observaciones": "x"})
    assert exc.value.codigo == "CONCURRENCIA"


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
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    assert client.get("/api/v1/ventas/pos/productos/?q=POS").status_code == 400
    buscar = client.get(f"/api/v1/ventas/pos/productos/?q=POS&id_sede={sede.id_sede}")
    assert buscar.status_code == 200
    assert client.get("/api/v1/ventas/facturas/").status_code == 200
    from django.utils import timezone

    mes = timezone.localdate().strftime("%Y-%m")
    assert client.get(f"/api/v1/ventas/facturas/estadisticas/?mes={mes}").status_code == 200
    assert client.get("/api/v1/ventas/facturas/999999/").status_code == 404
    body = {
        "id_sede": sede.id_sede,
        "id_tipo_venta": id_tipo,
        "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
        "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
        "clave_idempotencia": "pytest-epic8-emit-1",
    }
    emit = client.post("/api/v1/ventas/pos/emitir/", body, format="json")
    assert emit.status_code in (200, 201)
    pk = emit.json()["factura"]["id_factura"]
    assert client.get(f"/api/v1/ventas/facturas/{pk}/").status_code == 200
    dup = client.post("/api/v1/ventas/pos/emitir/", body, format="json")
    assert dup.status_code in (200, 201)
    assert client.post(
        f"/api/v1/ventas/facturas/{pk}/anular/",
        {"motivo": "corto"},
        format="json",
    ).status_code >= 400
    detalle = client.get(f"/api/v1/ventas/facturas/{pk}/").json()["factura"]
    dev = client.post(
        f"/api/v1/ventas/facturas/{pk}/devolucion/",
        {
            "motivo": "Producto dañado en transporte",
            "lineas": [{"id_detalle": detalle["lineas"][0]["id_detalle"], "cantidad": 1}],
        },
        format="json",
    )
    assert dev.status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_estadisticas_mes_y_catalogo_mensajeros(ctx: AuthContext) -> None:
    from django.utils import timezone

    prod, sede, id_tipo, id_ef = _producto_y_stock()
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 2}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 23800}],
        },
    )
    mes = timezone.localdate().strftime("%Y-%m")
    stats = svc.estadisticas_mes(ctx_sede, mes, sede.id_sede)
    assert stats["ventas"] >= 20000
    assert stats["ventas_dia"] >= 20000
    assert stats["devoluciones"] >= 0
    cat = svc.catalogos_pos()
    assert "mensajeros" in cat
    with pytest.raises(ReglaNegocioError):
        svc.estadisticas_mes(ctx_sede, "no-es-mes", None)


@pytest.mark.unit
@pytest.mark.django_db
def test_emitir_pos_con_domicilio_y_mensajero(ctx: AuthContext) -> None:
    from django.utils import timezone

    from apps.m07_domicilios.models import Mensajeros

    prod, sede, id_tipo, id_ef = _producto_y_stock()
    tipo_dom, _ = Tipos_venta.objects.get_or_create(nombre="Domicilio", defaults={"estado": True})
    Mensajeros.objects.create(
        nombre="Pos",
        apellido="Ruta",
        documento="POS-M",
        telefono="3001112233",
        fecha_inicio=timezone.localdate(),
        estado=True,
    )
    m = Mensajeros.objects.latest("id_mensajero")
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    out = svc.emitir(
        ctx_sede,
        {
            "id_sede": sede.id_sede,
            "id_tipo_venta": id_tipo,
            "es_domicilio": True,
            "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
            "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
            "domicilio": {
                "nombre": "Cliente Dom",
                "telefono": "+57300",
                "direccion": "Calle 10",
                "valor_cobrado_cliente": 5000,
                "valor_pagado_mensajero": 0,
                "id_mensajero": m.id_mensajero,
            },
        },
    )
    assert out["factura"]["requiere_domicilio"] is True
    assert tipo_dom.nombre == "Domicilio"
    lista = svc.listar(ctx_sede, {"numero": out["factura"]["numero_factura"][-3:]}, 1, 15)
    assert lista["total"] >= 1


@pytest.mark.unit
@pytest.mark.django_db
def test_emitir_domicilio_validaciones_campo(ctx: AuthContext) -> None:
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    Tipos_venta.objects.get_or_create(nombre="Domicilio", defaults={"estado": True})
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    body_base = {
        "id_sede": sede.id_sede,
        "id_tipo_venta": id_tipo,
        "es_domicilio": True,
        "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
        "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
    }
    with pytest.raises(ReglaNegocioError):
        svc.emitir(ctx_sede, {**body_base, "domicilio": {"nombre": " ", "telefono": "t", "direccion": "d", "id_mensajero": 1}})
    Tipos_venta.objects.filter(nombre__iexact="Domicilio").update(estado=False)
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
            {
                **body_base,
                "domicilio": {"nombre": "N", "telefono": "300", "direccion": "Calle", "id_mensajero": 1},
            },
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_emitir_domicilio_requiere_mensajero(ctx: AuthContext) -> None:
    prod, sede, id_tipo, id_ef = _producto_y_stock()
    Tipos_venta.objects.get_or_create(nombre="Domicilio", defaults={"estado": True})
    svc = AdminVentasService(audit=MagicMock())
    ctx_sede = _ctx_sede(ctx, sede)
    with pytest.raises(ReglaNegocioError):
        svc.emitir(
            ctx_sede,
            {
                "id_sede": sede.id_sede,
                "id_tipo_venta": id_tipo,
                "es_domicilio": True,
                "lineas": [{"id_producto": prod.id_producto, "cantidad": 1}],
                "pagos": [{"id_metodo_pago": id_ef, "valor": 11900}],
                "domicilio": {
                    "nombre": "Sin",
                    "telefono": "+57300",
                    "direccion": "Calle",
                    "id_mensajero": 0,
                },
            },
        )
