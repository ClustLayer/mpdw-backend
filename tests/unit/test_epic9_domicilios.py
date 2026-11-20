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
