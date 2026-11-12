"""Epic 5 — catálogo de productos backoffice."""

from decimal import Decimal

import pytest

from apps.m03_catalogo.admin_catalogo_service import AdminCatalogoService
from apps.m03_catalogo.mensajes import (
    MSG_CODIGO_DUP,
    MSG_CREADO,
    MSG_NOMBRE_OBL,
    MSG_OBLIGATORIOS,
    MSG_TIPO_BASE,
)
from apps.m03_catalogo.models import Categorias_producto, Marcas, Productos, Tipos_producto
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    return AuthContext(1, "a@test.local", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1")


@pytest.fixture
def params(db):
    cat = Categorias_producto.objects.create(nombre="Vinilos")
    marca = Marcas.objects.create(nombre="DECO")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Producto Terminado", defaults={"es_base": True})
    return cat, marca, tipo


def _payload(cat, marca, tipo, **extra):
    base = {
        "codigo_producto": "VIN-01",
        "nombre": "Vinilo blanco",
        "id_categoria": cat.id_categoria,
        "id_marca": marca.id_marca,
        "id_tipo_producto": tipo.id_tipo_producto,
        "unidad_medida": "UND",
        "precio_compra": "10.00",
        "precio_venta": "20.00",
        "iva_porcentaje": "19",
        "stock_minimo": 2,
        "inventario_habilitado": True,
    }
    base.update(extra)
    return base


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_y_listar(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    _, msg = svc.crear(ctx, _payload(cat, marca, tipo))
    assert msg == MSG_CREADO
    assert Productos.objects.filter(codigo_producto="VIN-01").exists()
    data = svc.listar("", {}, 1, 10, "nombre")
    assert data["total"] == 1
    assert "Mostrando 1 de 1" in data["mensaje"]


@pytest.mark.unit
@pytest.mark.django_db
def test_codigo_duplicado_y_obligatorios(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    svc.crear(ctx, _payload(cat, marca, tipo))
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear(ctx, _payload(cat, marca, tipo))
    assert exc.value.mensaje == MSG_CODIGO_DUP
    with pytest.raises(ReglaNegocioError) as vacio:
        svc.crear(ctx, {"codigo_producto": ""})
    assert vacio.value.mensaje == MSG_OBLIGATORIOS


@pytest.mark.unit
@pytest.mark.django_db
def test_precio_motivo_y_estado(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    det, _ = svc.crear(ctx, _payload(cat, marca, tipo))
    with pytest.raises(ReglaNegocioError):
        svc.editar(ctx, det["id_producto"], {**_payload(cat, marca, tipo), "precio_venta": "30", "version_fila": det["version_fila"]})
    det2, msg = svc.editar(
        ctx,
        det["id_producto"],
        {**_payload(cat, marca, tipo), "precio_venta": "30", "motivo": "Ajuste", "version_fila": det["version_fila"]},
    )
    assert "historial" in msg
    assert Decimal(det2["precio_venta"]) == Decimal("30.00")
    assert "correctamente" in svc.cambiar_estado(ctx, det["id_producto"], False)
    hist = svc.historial(det["id_producto"], "", "")
    assert hist["items"]


@pytest.mark.unit
@pytest.mark.django_db
def test_parametro_y_tipo_base(ctx, params):
    svc = AdminCatalogoService()
    msg = svc.crear_param(ctx, "categorias", {"nombre": "Esmaltes", "descripcion": ""})
    assert "creado correctamente" in msg
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear_param(ctx, "marcas", {"nombre": "  "})
    assert exc.value.mensaje == MSG_NOMBRE_OBL
    tipo = params[2]
    with pytest.raises(ReglaNegocioError) as base:
        svc.editar_param(ctx, "tipos", tipo.id_tipo_producto, {"nombre": tipo.nombre, "estado": False, "version_fila": tipo.version_fila})
    assert base.value.mensaje == MSG_TIPO_BASE


@pytest.mark.unit
@pytest.mark.django_db
def test_import_csv_no_sobrescribe(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    svc.crear(ctx, _payload(cat, marca, tipo))
    csv = (
        "codigo_producto,codigo_barras,nombre,descripcion,categoria,marca,tipo_producto,unidad_medida,precio_compra,precio_venta,iva_porcentaje,stock_minimo,inventario_habilitado\n"
        "VIN-01,,Otro,,Vinilos,DECO,Producto Terminado,UND,1,2,0,0,SI\n"
        "VIN-02,,Nuevo,,Vinilos,DECO,Producto Terminado,LT,1,2,0,0,NO\n"
    )
    res = svc.importar(ctx, "carga.csv", csv.encode())
    assert res["cargados"] == 1
    assert res["errores"]
    assert Productos.objects.get(codigo_producto="VIN-01").nombre == "Vinilo blanco"


@pytest.mark.unit
@pytest.mark.django_db
def test_reglas_extra_catalogo(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    det, _ = svc.crear(ctx, _payload(cat, marca, tipo, codigo_barras="123456"))
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, _payload(cat, marca, tipo, codigo_producto="VIN-09", codigo_barras="123456"))
    with pytest.raises(ReglaNegocioError):
        svc.historial(det["id_producto"], "2026-12-01", "2026-01-01")
    with pytest.raises(ReglaNegocioError):
        svc.editar(ctx, det["id_producto"], {**_payload(cat, marca, tipo, codigo_barras="123456"), "version_fila": 99})
    with pytest.raises(ReglaNegocioError):
        svc.guardar_imagen(det["id_producto"], "a.txt", b"no-image", "text/plain")
    with pytest.raises(ReglaNegocioError):
        svc.importar(ctx, "malo.txt", b"hola")
    marca2 = svc.crear_param(ctx, "marcas", {"nombre": "Otra"})
    assert "Marca" in marca2
    fila = Marcas.objects.get(nombre="Otra")
    assert "actualizado" in svc.editar_param(
        ctx, "marcas", fila.id_marca, {"nombre": "Otra", "estado": False, "version_fila": fila.version_fila}
    )
    csv = svc.exportar("", {"estado": "activo"}, "csv")
    assert csv[0].endswith(".csv")
    xlsx = svc.exportar("", {"estado": "activo"}, "xlsx")
    assert xlsx[0].endswith(".xlsx")
    with pytest.raises(ReglaNegocioError):
        svc.exportar("no-hay-nada-xyz", {}, "csv")
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, _payload(cat, marca, tipo, codigo_producto="BAD", unidad_medida="ZZ"))
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, _payload(cat, marca, tipo, codigo_producto="NEG", precio_compra="-1"))
    lista = svc.listar("Vinilo", {"estado": "activo", "stock": "agotado"}, 1, 10, "-nombre")
    assert lista["total"] >= 0
    from io import BytesIO

    from PIL import Image as PILImage

    buff = BytesIO()
    PILImage.new("RGB", (20, 20), "red").save(buff, format="PNG")
    ruta = svc.guardar_imagen(det["id_producto"], "a.png", buff.getvalue(), "image/png")
    assert ruta.endswith(".webp")
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["codigo_producto", "codigo_barras", "nombre", "descripcion", "categoria", "marca", "tipo_producto", "unidad_medida", "precio_compra", "precio_venta", "iva_porcentaje", "stock_minimo", "inventario_habilitado"])
    ws.append(["VIN-77", "", "Importado", "", "Vinilos", "DECO", "Producto Terminado", "UND", 1, 2, 0, 0, "NO"])
    raw = BytesIO()
    wb.save(raw)
    imp = svc.importar(ctx, "carga.xlsx", raw.getvalue())
    assert imp["cargados"] == 1


@pytest.mark.unit
@pytest.mark.django_db
def test_origen_comprado_fabricado(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    body, _ = svc.crear(ctx, _payload(cat, marca, tipo, codigo_producto="FAB-99", origen="fabricado"))
    assert body["origen"] == "fabricado"
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, _payload(cat, marca, tipo, codigo_producto="BAD-ORI", origen="importado"))
