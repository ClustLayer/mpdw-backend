from decimal import Decimal

import pytest
from django.utils import timezone

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m05_clientes.models import Clientes, Tipos_cliente
from apps.m06_ventas.models import Facturas, Tipos_venta
from apps.m07_domicilios.admin_domicilios_service import AdminDomiciliosService
from apps.m07_domicilios.mensajes import MSG_FACTURA_INVALIDA, MSG_MENSAJERO_INACTIVO
from apps.m07_domicilios.models import Entregas, Mensajeros
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="dom.epic9@test.local",
        password="Admin#2026demo",
        nombre="Dom",
        apellido="Epic9",
        documento="100009990399",
        id_rol=rol,
    )
    return AuthContext(user.id_usuario, user.email, "Administrador", (), True, id_rol=rol.id_rol, ip="127.0.0.1")


@pytest.fixture
def factura_domicilio(ctx: AuthContext) -> Facturas:
    sede = Sedes.objects.create(nombre="Sede Dom", direccion="Calle", estado=True, ciudad="BOG")
    tipo_cli, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"estado": True, "es_tipo_predeterminado": True})
    cliente = Clientes.objects.create(
        nombre="Ana",
        apellido="Lopez",
        numero_telefono="+573001112233",
        direccion="Calle 1 # 2-3",
        ciudad="Bogota",
        documento="909090",
        id_tipo_cliente=tipo_cli,
        estado=True,
    )
    tipo_dom, _ = Tipos_venta.objects.get_or_create(nombre="Domicilio", defaults={"estado": True})
    user = Usuarios.objects.get(pk=ctx.id_usuario)
    return Facturas.objects.create(
        id_sede=sede,
        serie="A",
        numero_factura="9001",
        id_cliente=cliente,
        id_usuario=user,
        id_tipo_venta=tipo_dom,
        subtotal=Decimal("10000"),
        total=Decimal("10000"),
        estado="EMITIDA",
    )


@pytest.fixture
def mensajero() -> Mensajeros:
    return Mensajeros.objects.create(
        nombre="Pedro",
        apellido="Ruta",
        documento="DOM-001",
        telefono="3001112233",
        fecha_inicio=timezone.localdate(),
        tarifa_promedio=Decimal("5000"),
        estado=True,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_domicilio_ok(ctx: AuthContext, factura_domicilio: Facturas) -> None:
    svc = AdminDomiciliosService()
    r = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Calle 5",
            "telefono_contacto": "+57300",
            "valor_cobrado_cliente": "3000",
            "valor_pagado_mensajero": "2000",
        },
    )
    assert "creado correctamente" in r["mensaje"]
    ent = Entregas.objects.get(pk=r["item"]["id_entrega"])
    assert ent.estado == "PENDIENTE"


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_rechaza_factura_mostrador(ctx: AuthContext, factura_domicilio: Facturas) -> None:
    tipo, _ = Tipos_venta.objects.get_or_create(nombre="Mostrador", defaults={"estado": True})
    factura_domicilio.id_tipo_venta = tipo
    factura_domicilio.save()
    with pytest.raises(ReglaNegocioError) as exc:
        AdminDomiciliosService().crear(
            ctx,
            {
                "id_factura": factura_domicilio.id_factura,
                "direccion": "X",
                "valor_cobrado_cliente": "0",
                "valor_pagado_mensajero": "0",
            },
        )
    assert exc.value.mensaje == MSG_FACTURA_INVALIDA


@pytest.mark.unit
@pytest.mark.django_db
def test_asignar_y_en_camino(ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
        },
    )
    id_entrega = creado["item"]["id_entrega"]
    svc.asignar_mensajero(ctx, id_entrega, {"id_mensajero": mensajero.id_mensajero})
    r = svc.cambiar_estado(ctx, id_entrega, {"estado": "EN_CAMINO"})
    assert r["item"]["estado"] == "EN_CAMINO"


@pytest.mark.unit
@pytest.mark.django_db
def test_en_camino_sin_mensajero(ctx: AuthContext, factura_domicilio: Facturas) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
        },
    )
    id_entrega = creado["item"]["id_entrega"]
    with pytest.raises(ReglaNegocioError):
        svc.cambiar_estado(ctx, id_entrega, {"estado": "EN_CAMINO"})


@pytest.mark.unit
@pytest.mark.django_db
def test_mensajero_inactivo(ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
        },
    )
    mensajero.estado = False
    mensajero.save()
    with pytest.raises(ReglaNegocioError) as exc:
        svc.asignar_mensajero(ctx, creado["item"]["id_entrega"], {"id_mensajero": mensajero.id_mensajero})
    assert exc.value.mensaje == MSG_MENSAJERO_INACTIVO


@pytest.mark.unit
@pytest.mark.django_db
def test_bandeja_antiguedad(ctx: AuthContext, factura_domicilio: Facturas) -> None:
    svc = AdminDomiciliosService()
    svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
        },
    )
    bandeja = svc.bandeja(None, None, None, None, None, "desc", 1, 20)
    assert bandeja["total"] == 1
    assert "antiguedad" in bandeja["items"][0]


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_con_mensajero_asignado(ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros) -> None:
    svc = AdminDomiciliosService()
    r = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "5000",
            "id_mensajero": mensajero.id_mensajero,
        },
    )
    assert r["item"]["estado"] == "ASIGNADO"
    assert r["item"]["mensajero"]


@pytest.mark.unit
@pytest.mark.django_db
def test_flujo_entregado(ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "1000",
            "valor_pagado_mensajero": "0",
            "id_mensajero": mensajero.id_mensajero,
        },
    )
    id_entrega = creado["item"]["id_entrega"]
    svc.cambiar_estado(ctx, id_entrega, {"estado": "EN_CAMINO"})
    r = svc.cambiar_estado(ctx, id_entrega, {"estado": "ENTREGADO"})
    assert r["item"]["estado"] == "ENTREGADO"
    assert svc.bandeja(None, None, None, None, None, "desc", 1, 20, vista="entregado")["total"] == 1


@pytest.mark.unit
@pytest.mark.django_db
def test_cancelar_domicilio(ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
            "id_mensajero": mensajero.id_mensajero,
        },
    )
    id_entrega = creado["item"]["id_entrega"]
    svc.cambiar_estado(ctx, id_entrega, {"estado": "EN_CAMINO"})
    r = svc.cambiar_estado(ctx, id_entrega, {"estado": "CANCELADO"})
    assert r["item"]["estado"] == "CANCELADO"


@pytest.mark.unit
@pytest.mark.django_db
def test_detalle_e_historial(ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
            "id_mensajero": mensajero.id_mensajero,
        },
    )
    id_entrega = creado["item"]["id_entrega"]
    det = svc.detalle(id_entrega)
    assert det["item"]["historial"]
    hist = svc.historial(mensajero.id_mensajero, None, None, None, None, 1, 20)
    assert hist["total"] >= 1


@pytest.mark.unit
@pytest.mark.django_db
def test_mensajeros_crud(ctx: AuthContext) -> None:
    svc = AdminDomiciliosService()
    creado = svc.mensajero_crear(
        ctx,
        {
            "nombre": "Luis",
            "apellido": "Vel",
            "documento": "DOM-900",
            "telefono": "3002223344",
            "fecha_inicio": timezone.localdate().isoformat(),
            "tarifa_promedio": "8000",
        },
    )
    mid = creado["item"]["id_mensajero"]
    lista = svc.mensajeros_listar("Luis", "activo", 1, 10)
    assert lista["total"] >= 1
    assert svc.mensajeros_activos()["items"]
    svc.mensajero_actualizar(
        ctx,
        mid,
        {
            "nombre": "Luis",
            "apellido": "Veloz",
            "documento": "DOM-900",
            "telefono": "3002223344",
            "fecha_inicio": timezone.localdate().isoformat(),
            "tarifa_promedio": "9000",
            "version_fila": 1,
        },
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_transicion_invalida(ctx: AuthContext, factura_domicilio: Facturas) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
        },
    )
    with pytest.raises(ReglaNegocioError):
        svc.cambiar_estado(ctx, creado["item"]["id_entrega"], {"estado": "ENTREGADO"})


@pytest.mark.unit
@pytest.mark.django_db
def test_precarga_y_historial_vacio(ctx: AuthContext, factura_domicilio: Facturas) -> None:
    svc = AdminDomiciliosService()
    pre = svc.precarga_factura(factura_domicilio.id_factura)
    assert pre["direccion"]
    vacio = svc.historial(None, None, None, None, "ENTREGADO", 1, 20)
    assert vacio["total"] == 0
    assert svc.bandeja(None, None, None, None, None, "desc", 1, 20, vista="todos")["items"] is not None


@pytest.mark.unit
@pytest.mark.django_db
def test_validaciones_crear_y_precarga(
    ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros
) -> None:
    svc = AdminDomiciliosService()
    with pytest.raises(ReglaNegocioError):
        svc.precarga_factura(9_999_999)
    tipo_mostrador, _ = Tipos_venta.objects.get_or_create(nombre="Mostrador", defaults={"estado": True})
    otra = Facturas.objects.create(
        id_sede=factura_domicilio.id_sede,
        serie="B",
        numero_factura="1",
        id_usuario=factura_domicilio.id_usuario,
        id_tipo_venta=tipo_mostrador,
        subtotal=Decimal("1"),
        total=Decimal("1"),
        estado="EMITIDA",
    )
    with pytest.raises(ReglaNegocioError):
        svc.precarga_factura(otra.id_factura)
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            ctx,
            {
                "id_factura": factura_domicilio.id_factura,
                "direccion": "",
                "valor_cobrado_cliente": "0",
                "valor_pagado_mensajero": "0",
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            ctx,
            {
                "id_factura": factura_domicilio.id_factura,
                "direccion": "x" * 256,
                "valor_cobrado_cliente": "0",
                "valor_pagado_mensajero": "0",
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            ctx,
            {
                "id_factura": factura_domicilio.id_factura,
                "direccion": "Ok",
                "telefono_contacto": "teléfono inválido !!!",
                "valor_cobrado_cliente": "no-num",
                "valor_pagado_mensajero": "0",
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            ctx,
            {
                "id_factura": factura_domicilio.id_factura,
                "direccion": "Ok",
                "valor_cobrado_cliente": "-1",
                "valor_pagado_mensajero": "0",
            },
        )
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Dir activa",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
        },
    )
    with pytest.raises(ReglaNegocioError):
        svc.precarga_factura(factura_domicilio.id_factura)
    with pytest.raises(ReglaNegocioError):
        svc.asignar_mensajero(ctx, creado["item"]["id_entrega"], {"id_mensajero": 0})
    with pytest.raises(ReglaNegocioError):
        svc.asignar_mensajero(ctx, creado["item"]["id_entrega"], {"id_mensajero": mensajero.id_mensajero + 99})


@pytest.mark.unit
@pytest.mark.django_db
def test_bandeja_filtros_y_detalle(ctx: AuthContext, factura_domicilio: Facturas, mensajero: Mensajeros) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Filtros",
            "valor_cobrado_cliente": "100",
            "valor_pagado_mensajero": "0",
            "id_mensajero": mensajero.id_mensajero,
        },
    )
    id_ent = creado["item"]["id_entrega"]
    hoy = timezone.localdate().isoformat()
    asc = svc.bandeja(None, mensajero.id_mensajero, hoy, hoy, factura_domicilio.id_sede_id, "asc", 1, 10, vista="activos")
    assert asc["total"] >= 1
    assert svc.bandeja("ASIGNADO", None, None, None, None, "desc", 1, 10, vista="activos")["total"] >= 1
    assert svc.bandeja(None, None, None, None, None, "desc", 1, 10, vista="entregado")["total"] == 0
    vacia = svc.bandeja(None, 99999, None, None, None, "desc", 1, 10)
    assert vacia["total"] == 0
    det = svc.detalle(id_ent)
    assert det["item"]["id_entrega"] == id_ent
    with pytest.raises(ReglaNegocioError):
        svc.detalle(888888)
    hist = svc.historial(mensajero.id_mensajero, factura_domicilio.id_cliente_id, hoy, hoy, "ASIGNADO", 1, 10)
    assert hist["total"] >= 1


@pytest.mark.unit
@pytest.mark.django_db
def test_mensajero_validaciones_y_concurrencia(ctx: AuthContext) -> None:
    svc = AdminDomiciliosService()
    futuro = (timezone.localdate().replace(year=timezone.localdate().year + 1)).isoformat()
    with pytest.raises(ReglaNegocioError):
        svc.mensajero_crear(
            ctx,
            {
                "nombre": "X",
                "apellido": "Y",
                "documento": "DOC-VAL",
                "telefono": "300",
                "fecha_inicio": futuro,
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.mensajero_crear(ctx, {"nombre": "", "apellido": "Y", "documento": "D", "telefono": "300", "fecha_inicio": "2020-01-01"})
    uno = svc.mensajero_crear(
        ctx,
        {
            "nombre": "Uno",
            "apellido": "Dup",
            "documento": "UNICO-DUP",
            "telefono": "3001110000",
            "fecha_inicio": timezone.localdate().isoformat(),
        },
    )
    with pytest.raises(ReglaNegocioError):
        svc.mensajero_crear(
            ctx,
            {
                "nombre": "Dos",
                "apellido": "Dup",
                "documento": "UNICO-DUP",
                "telefono": "3001110001",
                "fecha_inicio": timezone.localdate().isoformat(),
            },
        )
    mid = uno["item"]["id_mensajero"]
    with pytest.raises(ReglaNegocioError):
        svc.mensajero_actualizar(ctx, mid, {"version_fila": 99, "nombre": "Uno"})
    assert svc.mensajeros_listar("Uno", "activo", 1, 10)["total"] >= 1
    assert svc.mensajeros_listar("", "inactivo", 1, 10)["total"] == 0


@pytest.mark.unit
@pytest.mark.django_db
def test_cambiar_estado_validaciones(ctx: AuthContext, factura_domicilio: Facturas) -> None:
    svc = AdminDomiciliosService()
    creado = svc.crear(
        ctx,
        {
            "id_factura": factura_domicilio.id_factura,
            "direccion": "Estado",
            "valor_cobrado_cliente": "0",
            "valor_pagado_mensajero": "0",
        },
    )
    id_ent = creado["item"]["id_entrega"]
    with pytest.raises(ReglaNegocioError):
        svc.cambiar_estado(ctx, id_ent, {"estado": ""})
    with pytest.raises(ReglaNegocioError):
        svc.cambiar_estado(ctx, 999999, {"estado": "EN_CAMINO"})
    sin_user = AuthContext(999999999, "ghost@test", "Administrador", (), True)
    with pytest.raises(ReglaNegocioError):
        svc.cambiar_estado(sin_user, id_ent, {"estado": "CANCELADO"})


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_sin_usuario_en_ctx(factura_domicilio: Facturas) -> None:
    svc = AdminDomiciliosService()
    sin_user = AuthContext(None, "anon@test", "Administrador", (), True)
    fantasma = AuthContext(888888888, "ghost@test", "Administrador", (), True)
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            fantasma,
            {
                "id_factura": factura_domicilio.id_factura,
                "direccion": "Dir",
                "valor_cobrado_cliente": "0",
                "valor_pagado_mensajero": "0",
            },
        )
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            sin_user,
            {
                "id_factura": factura_domicilio.id_factura,
                "direccion": "Dir",
                "valor_cobrado_cliente": "0",
                "valor_pagado_mensajero": "0",
            },
        )
