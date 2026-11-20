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
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from apps.m14_proveedores.models import TIPO_DOC_NIT, Proveedores
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    return AuthContext(0, "a@test.local", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1")


@pytest.mark.unit
@pytest.mark.django_db
def test_entrada_y_traslado(ctx):
    cat = Categorias_producto.objects.create(nombre="Cat Inv")
    marca = Marcas.objects.create(nombre="Marca Inv")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Producto Terminado", defaults={"es_base": True})
    sede_a = Sedes.objects.create(nombre="Sede A", direccion="Calle 1", estado=True)
    sede_b = Sedes.objects.create(nombre="Sede B", direccion="Calle 2", estado=True)
    prod = Productos.objects.create(
        codigo_producto="INV-1",
        nombre="Pintura",
        id_categoria=cat,
        id_marca=marca,
        id_tipo_producto=tipo,
        precio_venta=Decimal("10"),
        unidad_medida="UND",
    )
    prov = Proveedores.objects.create(nombre="Proveedor Demo", tipo_documento=TIPO_DOC_NIT, estado=True)
    svc = AdminInventarioService()
    msg = svc.entrada(
        ctx,
        {
            "id_producto": prod.id_producto,
            "id_sede": sede_a.id_sede,
            "cantidad": "5",
            "motivo": "Compra",
            "id_proveedor": prov.id_proveedor,
            "costo_unitario": "8",
        },
    )
    assert "correctamente" in msg
    assert Inventarios.objects.get(id_producto=prod, id_sede=sede_a).cantidad_actual == 5
    svc.traslado(ctx, {"id_producto": prod.id_producto, "id_sede": sede_a.id_sede, "id_sede_destino": sede_b.id_sede, "cantidad": "2", "motivo": "Traslado"})
    assert Inventarios.objects.get(id_producto=prod, id_sede=sede_a).cantidad_actual == 3
    with pytest.raises(ReglaNegocioError):
        svc.ajuste(ctx, {"id_producto": prod.id_producto, "id_sede": sede_a.id_sede, "cantidad": "9", "motivo": "Baja", "tipo": "merma"})
    data = svc.existencias("Pintura", None)
    assert data["items"]
    assert svc.kardex({"tipo": "entrada_compra"})["items"]
    svc.ajuste(ctx, {"id_producto": prod.id_producto, "id_sede": sede_a.id_sede, "cantidad": "1", "motivo": "Sobra", "tipo": "ajuste_positivo"})


@pytest.mark.unit
@pytest.mark.django_db
def test_api_inventario():
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="inv.admin@test.local", password="Admin#2026demo", nombre="Inv", apellido="Admin", documento="100009990188", id_rol=rol
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-inv"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/inventario/existencias/").status_code == 200
    assert client.get("/api/v1/inventario/kardex/").status_code == 200
    assert client.get("/api/v1/inventario/productos-opciones/?q=").status_code == 200
    assert client.get("/api/v1/inventario/proveedores-activos/").status_code == 200
    assert client.post("/api/v1/inventario/movimientos/entrada-lote/", {"id_sede": 1, "lineas": []}, format="json").status_code == 400
    assert client.post("/api/v1/inventario/movimientos/nope/", {}, format="json").status_code == 404
    assert client.post("/api/v1/inventario/movimientos/entrada/", {}, format="json").status_code == 400


@pytest.mark.unit
@pytest.mark.django_db
def test_existencias_busca_barras(ctx):
    cat = Categorias_producto.objects.create(nombre="Cat Bar")
    marca = Marcas.objects.create(nombre="Marca Bar")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True})
    Productos.objects.create(
        codigo_producto="BAR-1",
        codigo_barras="7701234567890",
        nombre="Con barras",
        id_categoria=cat,
        id_marca=marca,
        id_tipo_producto=tipo,
        precio_venta=Decimal("1"),
        unidad_medida="UND",
    )
    svc = AdminInventarioService()
    assert svc.existencias("7701234567890", None)["items"]
    assert svc.productos_opciones("BAR")["items"]


@pytest.mark.unit
@pytest.mark.django_db
def test_entrada_proveedor_y_fabricado(ctx):
    cat = Categorias_producto.objects.create(nombre="Cat Ori")
    marca = Marcas.objects.create(nombre="Marca Ori")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Insumo", defaults={"es_base": True})
    sede = Sedes.objects.create(nombre="Sede Ori", direccion="Calle 3", estado=True)
    comprado = Productos.objects.create(
        codigo_producto="CMP-1",
        nombre="Comprado",
        id_categoria=cat,
        id_marca=marca,
        id_tipo_producto=tipo,
        precio_venta=Decimal("10"),
        unidad_medida="UND",
        origen=Productos.ORIGEN_COMPRADO,
    )
    fabricado = Productos.objects.create(
        codigo_producto="FAB-1",
        nombre="Fabricado",
        id_categoria=cat,
        id_marca=marca,
        id_tipo_producto=tipo,
        precio_venta=Decimal("10"),
        unidad_medida="UND",
        origen=Productos.ORIGEN_FABRICADO,
    )
    prov = Proveedores.objects.create(nombre="ACME", tipo_documento=TIPO_DOC_NIT, estado=True)
    svc = AdminInventarioService()
    with pytest.raises(ReglaNegocioError):
        svc.entrada(ctx, {"id_producto": comprado.id_producto, "id_sede": sede.id_sede, "cantidad": "1", "motivo": "x"})
    svc.entrada(
        ctx,
        {
            "id_producto": comprado.id_producto,
            "id_sede": sede.id_sede,
            "cantidad": "1",
            "motivo": "x",
            "id_proveedor": prov.id_proveedor,
        },
    )
    svc.entrada(ctx, {"id_producto": fabricado.id_producto, "id_sede": sede.id_sede, "cantidad": "1", "motivo": "Prod interna"})
    lote = svc.entrada_lote(
        ctx,
        {
            "id_sede": sede.id_sede,
            "id_proveedor": prov.id_proveedor,
            "lineas": [{"codigo": "FAB-1", "cantidad": "2", "costo_unitario": "5"}],
        },
    )
    assert "registrada" in lote
    data = svc.productos_opciones("Comprado")
    assert data["items"]
    k = svc.kardex({})
    assert any(i.get("costo_unitario") for i in k["items"])
    with pytest.raises(ReglaNegocioError):
        svc.entrada(ctx, {"id_producto": comprado.id_producto, "id_sede": sede.id_sede, "cantidad": "1", "motivo": "x", "costo_unitario": "-1"})
    with pytest.raises(ReglaNegocioError):
        svc.entrada_lote(ctx, {"id_sede": sede.id_sede, "lineas": [{"id_producto": comprado.id_producto, "cantidad": "1"}]})
    with pytest.raises(ReglaNegocioError):
        svc._resolver_producto({"codigo": "ZZZ-NO-EXISTE"})
    svc.entrada_lote(
        ctx,
        {
            "id_sede": sede.id_sede,
            "id_proveedor": prov.id_proveedor,
            "lineas": [
                {"id_producto": comprado.id_producto, "cantidad": "1"},
                {"id_producto": comprado.id_producto, "cantidad": "2"},
            ],
        },
    )
    svc.kardex({"desde": "2020-01-01", "hasta": "2099-12-31", "tipo": "entrada_compra", "id_sede": str(sede.id_sede)})
    with pytest.raises(ReglaNegocioError):
        svc.entrada(
            ctx,
            {"id_producto": 0, "id_sede": sede.id_sede, "cantidad": "1", "motivo": "x", "id_proveedor": prov.id_proveedor},
        )
    with pytest.raises(ReglaNegocioError):
        svc.entrada_lote(ctx, {"id_sede": 0, "lineas": [{"id_producto": comprado.id_producto, "cantidad": "1"}]})
    with pytest.raises(ReglaNegocioError):
        svc.ajuste(ctx, {"id_producto": comprado.id_producto, "id_sede": sede.id_sede, "cantidad": "1", "motivo": "x", "tipo": "invalido"})
    assert AdminInventarioService().totales()["existencia_total"] >= 0
    inactivo = Proveedores.objects.create(nombre="Inactivo", tipo_documento=TIPO_DOC_NIT, estado=False)
    with pytest.raises(ReglaNegocioError):
        svc.entrada(
            ctx,
            {
                "id_producto": comprado.id_producto,
                "id_sede": sede.id_sede,
                "cantidad": "1",
                "motivo": "x",
                "id_proveedor": inactivo.id_proveedor,
            },
        )
    svc.entrada(
        ctx,
        {
            "id_producto": comprado.id_producto,
            "id_sede": sede.id_sede,
            "cantidad": "1",
            "motivo": "x",
            "proveedor": str(prov.id_proveedor),
        },
    )
    assert svc.proveedores_activos()["items"]
    with pytest.raises(ReglaNegocioError):
        svc._resolver_id_proveedor({"id_proveedor": 999999})
