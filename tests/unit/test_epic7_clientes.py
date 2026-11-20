from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m02_sedes.models import Sedes
from apps.m05_clientes.admin_clientes_service import AdminClientesService, whatsapp_habilitado
from apps.m05_clientes.models import Clientes, Tipos_cliente
from apps.m06_ventas.models import Detalle_factura, Facturas, Tipos_venta
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    return AuthContext(0, "a@test.local", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1")


@pytest.mark.unit
@pytest.mark.django_db
def test_cliente_crud_y_duplicado(ctx):
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    svc = AdminClientesService(audit=MagicMock())
    body = {
        "nombre": "Ana",
        "apellido": "López",
        "numero_telefono": "+573001234567",
        "tiene_whatsapp": True,
        "id_tipo_cliente": com.id_tipo_cliente,
        "consentimiento_datos": True,
    }
    out = svc.crear(ctx, body)
    assert "correctamente" in out["mensaje"]
    dup = svc.verificar_telefono("+573001234567")
    assert dup
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear(ctx, {**body, "nombre": "Otra"})
    assert exc.value.codigo == "TELEFONO_DUPLICADO"
    pk = out["cliente"]["id_cliente"]
    ok = svc.crear(ctx, {**body, "nombre": "Otra", "confirmar_duplicado": True})
    assert ok["cliente"]["nombre"] == "Otra"
    patch = svc.actualizar(
        ctx,
        pk,
        {**body, "ciudad": "Cali", "version_fila": 1, "estado": True, "confirmar_duplicado": True},
    )
    assert patch["cliente"]["ciudad"] == "Cali"


@pytest.mark.unit
@pytest.mark.django_db
def test_tipo_comun_protegido(ctx):
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    svc = AdminClientesService(audit=MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_tipo(ctx, com.id_tipo_cliente, {"nombre": "Común", "version_fila": 1})
    with pytest.raises(ReglaNegocioError):
        svc.crear_tipo(ctx, {"nombre": "Común"})


@pytest.mark.unit
@pytest.mark.django_db
def test_api_clientes():
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="cli.admin@test.local",
        password="Admin#2026demo",
        nombre="Cli",
        apellido="Admin",
        documento="100009990199",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-cli"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/clientes/").status_code == 200
    r = client.post(
        "/api/v1/clientes/",
        {
            "nombre": "Pedro",
            "numero_telefono": "+573009998877",
            "id_tipo_cliente": com.id_tipo_cliente,
            "consentimiento_datos": True,
        },
        format="json",
    )
    assert r.status_code == 201
    assert client.get("/api/v1/clientes/tipos/").status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_y_validaciones(ctx):
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    svc = AdminClientesService(audit=MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"nombre": "X", "numero_telefono": "bad", "id_tipo_cliente": com.id_tipo_cliente})
    svc.crear(
        ctx,
        {
            "nombre": "Luis",
            "numero_telefono": "+573001112222",
            "id_tipo_cliente": com.id_tipo_cliente,
            "consentimiento_datos": True,
        },
    )
    data = svc.listar("Luis", None, "activo", 1, 10)
    assert data["items"]
    assert svc.tipos_listado()["items"]


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.django_db
def test_historial_cliente_inexistente(ctx):
    with pytest.raises(ReglaNegocioError):
        AdminClientesService().historial(ctx, 9_999_999, None, None, 1, 10, False)


def test_whatsapp_helper():
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    c = Clientes.objects.create(
        nombre="W",
        numero_telefono="+573009999888",
        tiene_whatsapp=True,
        id_tipo_cliente=com,
    )
    ok, url, _ = whatsapp_habilitado(c)
    assert ok and url.endswith("573009999888")
    c.tiene_whatsapp = False
    assert not whatsapp_habilitado(c)[0]


@pytest.mark.unit
@pytest.mark.django_db
def test_historial_metricas(ctx):
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    c = Clientes.objects.create(
        nombre="Cliente",
        numero_telefono="+573001110000",
        id_tipo_cliente=com,
        consentimiento_datos=True,
        fecha_consentimiento=timezone.now(),
    )
    sede = Sedes.objects.create(nombre="S1", direccion="X", estado=True)
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True})
    user = Usuarios.objects.create_user(
        email="h@test.local",
        password="Admin#2026demo",
        nombre="H",
        apellido="U",
        documento="10088",
        id_rol=rol,
    )
    tv, _ = Tipos_venta.objects.get_or_create(nombre="POS")
    f = Facturas.objects.create(
        serie="A",
        numero_factura=9,
        id_sede=sede,
        id_usuario=user,
        id_cliente=c,
        id_tipo_venta=tv,
        subtotal=Decimal("100"),
        total=Decimal("100"),
        estado="EMITIDA",
    )
    from apps.m03_catalogo.models import Categorias_producto, Productos

    cat = Categorias_producto.objects.create(nombre="Cat")
    prod = Productos.objects.create(
        codigo_producto="P-CLI",
        nombre="Látex",
        id_categoria=cat,
        precio_venta=Decimal("10"),
        version=1,
    )
    Detalle_factura.objects.create(id_factura=f, id_producto=prod, cantidad=Decimal("2"), subtotal=Decimal("100"))
    data = AdminClientesService().historial(ctx, c.id_cliente, None, None, 1, 10, True)
    assert data["resumen"]["num_compras"] == 1
    assert data["metricas"]["productos_frecuentes"]


@pytest.mark.unit
@pytest.mark.django_db
def test_flujos_extra(ctx):
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    svc = AdminClientesService(audit=MagicMock())
    vacio = svc.listar("zzzz-no-existe", None, "todos", 1, 10)
    assert vacio["mensaje"]
    tipo = svc.crear_tipo(ctx, {"nombre": "Pintor pro"})
    assert "correctamente" in tipo["mensaje"]
    out = svc.crear(
        ctx,
        {
            "nombre": "Zoe",
            "numero_telefono": "+573004445566",
            "id_tipo_cliente": com.id_tipo_cliente,
            "consentimiento_datos": False,
        },
    )
    det = svc.obtener(out["cliente"]["id_cliente"])
    assert det["nombre"] == "Zoe"
    hist = svc.historial(ctx, det["id_cliente"], None, None, 1, 10, False)
    assert hist["mensaje"]
    with pytest.raises(ReglaNegocioError):
        svc.actualizar(ctx, det["id_cliente"], {"version_fila": 99, "nombre": "X", "numero_telefono": "+573004445566", "id_tipo_cliente": com.id_tipo_cliente})
    ok = svc.actualizar(
        ctx,
        det["id_cliente"],
        {
            "nombre": "Zoe",
            "numero_telefono": "+573004445566",
            "id_tipo_cliente": com.id_tipo_cliente,
            "ciudad": "Palmira",
            "version_fila": det["version_fila"],
            "estado": True,
            "consentimiento_datos": True,
        },
    )
    assert ok["cliente"]["ciudad"] == "Palmira"
    dup = svc.crear_tipo(ctx, {"nombre": "Contratista"})
    svc.actualizar_tipo(
        ctx,
        dup["tipo"]["id_tipo_cliente"],
        {"nombre": "Contratista VIP", "version_fila": dup["tipo"]["version_fila"], "estado": True},
    )
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"nombre": "", "numero_telefono": "+573001111111", "id_tipo_cliente": com.id_tipo_cliente})
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"nombre": "Bad", "numero_telefono": "+573001111111", "correo": "no", "id_tipo_cliente": com.id_tipo_cliente})


@pytest.mark.unit
@pytest.mark.django_db
def test_api_clientes_historial():
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="cli.hist@test.local",
        password="Admin#2026demo",
        nombre="H",
        apellido="A",
        documento="100009990288",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-cli-h"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    cr = client.post(
        "/api/v1/clientes/",
        {
            "nombre": "Marta",
            "numero_telefono": "+573006667788",
            "id_tipo_cliente": com.id_tipo_cliente,
        },
        format="json",
    )
    assert cr.status_code == 201
    pk = cr.json()["cliente"]["id_cliente"]
    assert client.get(f"/api/v1/clientes/{pk}/historial/").status_code == 200
    assert client.get("/api/v1/clientes/verificar-telefono/?numero_telefono=%2B573006667788").status_code == 200
    patch = client.patch(
        f"/api/v1/clientes/{pk}/",
        {
            "nombre": "Marta",
            "numero_telefono": "+573006667788",
            "id_tipo_cliente": com.id_tipo_cliente,
            "version_fila": 1,
            "estado": True,
        },
        format="json",
    )
    assert patch.status_code == 200
    conflict = client.patch(
        f"/api/v1/clientes/{pk}/",
        {
            "nombre": "Marta",
            "numero_telefono": "+573006667788",
            "id_tipo_cliente": com.id_tipo_cliente,
            "version_fila": 999,
            "estado": True,
        },
        format="json",
    )
    assert conflict.status_code == 409
    assert client.get("/api/v1/clientes/999999/").status_code == 404
    bad = client.post("/api/v1/clientes/", {"nombre": "", "numero_telefono": "x"}, format="json")
    assert bad.status_code == 400
    assert client.post("/api/v1/clientes/tipos/", {"nombre": "Común"}, format="json").status_code == 400
    assert client.post("/api/v1/clientes/tipos/", {"nombre": "Empresa E2E"}, format="json").status_code == 201


@pytest.mark.unit
@pytest.mark.django_db
def test_documento_con_factura(ctx):
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    c = Clientes.objects.create(
        nombre="Fact",
        documento="9001",
        numero_telefono="+573003331111",
        id_tipo_cliente=com,
    )
    sede = Sedes.objects.create(nombre="S2", direccion="Y", estado=True)
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True})
    user = Usuarios.objects.create_user(
        email="f@test.local", password="Admin#2026demo", nombre="F", apellido="T", documento="99", id_rol=rol
    )
    tv, _ = Tipos_venta.objects.get_or_create(nombre="POS")
    Facturas.objects.create(
        serie="B",
        numero_factura=2,
        id_sede=sede,
        id_usuario=user,
        id_cliente=c,
        id_tipo_venta=tv,
        subtotal=Decimal("1"),
        total=Decimal("1"),
        estado="EMITIDA",
    )
    svc = AdminClientesService(audit=MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc.actualizar(
            ctx,
            c.id_cliente,
            {
                "nombre": "Fact",
                "documento": "9002",
                "numero_telefono": "+573003331111",
                "id_tipo_cliente": com.id_tipo_cliente,
                "version_fila": c.version_fila,
                "estado": True,
            },
        )
    Clientes.objects.create(nombre="Ina", numero_telefono="+573004442222", id_tipo_cliente=com, estado=False)
    assert svc.listar("", None, "inactivo", 1, 10)["items"]
    ok, _, mot = whatsapp_habilitado(Clientes(nombre="X", numero_telefono="123", tiene_whatsapp=True, id_tipo_cliente=com))
    assert not ok and mot


@pytest.mark.unit
@pytest.mark.django_db
def test_filtro_tipo_y_metricas_gerente():
    com, _ = Tipos_cliente.objects.get_or_create(nombre="Común", defaults={"es_tipo_predeterminado": True})
    pintor = Tipos_cliente.objects.create(nombre="Pintor QA", estado=True)
    Clientes.objects.create(nombre="TipoA", numero_telefono="+573005551111", id_tipo_cliente=pintor)
    svc = AdminClientesService(audit=MagicMock())
    filtrado = svc.listar("", pintor.id_tipo_cliente, "activo", 1, 10)
    assert len(filtrado["items"]) == 1
    ctx_g = AuthContext(1, "g@test.local", "Gerente", (1,), True, id_rol=2, ip="127.0.0.1")
    c = Clientes.objects.create(nombre="Met", numero_telefono="+573007771111", id_tipo_cliente=com)
    # sin facturas: métricas pueden ser null; validamos rol y filtro
    assert svc.historial(ctx_g, c.id_cliente, None, None, 1, 10, True)["metricas"] is None
    assert AdminClientesService().tipo_predeterminado_id() == com.id_tipo_cliente
    with pytest.raises(ReglaNegocioError):
        svc.crear_tipo(ctx_g, {"nombre": "Pintor QA"})
    assert svc.tipos_listado(solo_activos=True)["items"]
