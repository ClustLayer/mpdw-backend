"""Sprint 2 — diez mejoras (catálogo, clientes, panel, eventos)."""

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.panel_resumen_service import construir_panel_resumen
from apps.m01_identidad.services import AuthService
from apps.m03_catalogo.admin_catalogo_service import AdminCatalogoService
from apps.m03_catalogo.mensajes import MSG_TIPO_BASE
from apps.m03_catalogo.models import Categorias_producto, Marcas, Productos, Tipos_producto
from apps.m05_clientes.admin_clientes_service import AdminClientesService
from apps.m05_clientes.mensajes import MSG_TIPO_COLOR_INVALIDO
from apps.m05_clientes.models import Tipos_cliente
from apps.m10_auditoria.models import Auditoria
from apps.m11_eventos.admin_eventos_service import AdminEventosService
from apps.m11_eventos.models import TIPO_PROMOCION
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    return AuthContext(1, "a@test.local", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1")


@pytest.fixture
def params(db):
    cat = Categorias_producto.objects.create(nombre="Vinilos S2")
    marca = Marcas.objects.create(nombre="DECO S2")
    tipo, _ = Tipos_producto.objects.get_or_create(nombre="Producto Terminado", defaults={"es_base": True})
    return cat, marca, tipo


def _payload(cat, marca, tipo, **extra):
    return {
        "codigo_producto": "S2-01",
        "nombre": "Producto sprint2",
        "id_categoria": cat.id_categoria,
        "id_marca": marca.id_marca,
        "id_tipo_producto": tipo.id_tipo_producto,
        "unidad_medida": "UND",
        "precio_compra": "10.00",
        "precio_venta": "20.00",
        "iva_porcentaje": "19",
        "stock_minimo": 2,
        "inventario_habilitado": True,
        **extra,
    }


@pytest.mark.unit
@pytest.mark.django_db
def test_categoria_set_null_al_eliminar_param(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    det, _ = svc.crear(ctx, _payload(cat, marca, tipo, codigo_producto="NULL-CAT"))
    pid = det["id_producto"]
    msg = svc.eliminar_param(ctx, "categorias", cat.id_categoria)
    assert "eliminado" in msg.lower()
    p = Productos.objects.get(pk=pid)
    assert p.id_categoria_id is None
    lista = svc.listar("", {}, 1, 10, "categoria")
    assert lista["items"][0]["categoria"] == ""
    orden = svc.listar("", {}, 1, 10, "-categoria")
    assert orden["total"] >= 1


@pytest.mark.unit
@pytest.mark.django_db
def test_eliminar_tipo_base_bloqueado(ctx, params):
    svc = AdminCatalogoService()
    tipo = params[2]
    with pytest.raises(ReglaNegocioError) as exc:
        svc.eliminar_param(ctx, "tipos", tipo.id_tipo_producto)
    assert exc.value.mensaje == MSG_TIPO_BASE


@pytest.mark.unit
@pytest.mark.django_db
def test_export_extendido(ctx, params):
    cat, marca, tipo = params
    svc = AdminCatalogoService()
    svc.crear(ctx, _payload(cat, marca, tipo, codigo_producto="EXP-01", origen="fabricado"))
    nombre, raw, _ = svc.exportar("", {"estado": "activo"}, "csv")
    assert nombre.endswith("-catalogo-productos.csv")
    texto = raw.decode("utf-8-sig")
    assert "precio_compra" in texto
    assert "iva_porcentaje" in texto
    assert "Fabricado" in texto
    _, xlsx, _ = svc.exportar("", {"estado": "activo"}, "xlsx", alcance="pagina", page=1, page_size=1)
    assert xlsx[:2] == b"PK"


@pytest.mark.unit
@pytest.mark.django_db
def test_tipo_cliente_color(ctx):
    svc = AdminClientesService(audit=MagicMock())
    admin = AuthContext(1, "a@test.local", "Administrador", (1,), True, id_rol=1)
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear_tipo(admin, {"nombre": "VIP color", "color": "rojo"})
    assert exc.value.mensaje == MSG_TIPO_COLOR_INVALIDO
    out = svc.crear_tipo(admin, {"nombre": "VIP color", "color": "#E11D74"})
    assert out["tipo"]["color"] == "#E11D74"
    com = Tipos_cliente.objects.filter(nombre__iexact="Común").first()
    if com:
        assert com.color == "#64748B"


@pytest.mark.unit
@pytest.mark.django_db
def test_panel_resumen_permisos(ctx, db):
    con_inv = construir_panel_resumen(ctx)
    assert "inventario" in con_inv
    assert "bajo_stock_minimo" in con_inv["inventario"]
    Auditoria.objects.create(accion="LOGIN", entidad="Usuarios", id_entidad=1, motivo="test", resultado="EXITO")
    con_aud = construir_panel_resumen(ctx)
    assert "actividad_reciente" in con_aud
    assert con_aud["actividad_reciente"]
    sin_ctx = AuthContext(99, "x@test.local", "SinPermiso", (), True, id_rol=9999)
    vacio = construir_panel_resumen(sin_ctx)
    assert "inventario" not in vacio
    assert "actividad_reciente" not in vacio


@pytest.mark.unit
@pytest.mark.django_db
def test_evento_imagen_y_publicos(ctx):
    svc = AdminEventosService(audit=MagicMock())
    from django.utils import timezone

    out = svc.crear(
        ctx,
        {
            "tipo": TIPO_PROMOCION,
            "titulo": "Con imagen",
            "descripcion": "Test",
            "fecha_inicio": timezone.now().isoformat(),
            "visible_sitio": True,
        },
    )
    pk = out["evento"]["id_evento"]
    buff = BytesIO()
    Image.new("RGB", (32, 32), "blue").save(buff, format="PNG")
    ruta = svc.guardar_imagen_evento(pk, "ev.png", buff.getvalue(), "image/png")
    assert ruta.startswith("eventos/")
    pub = svc.publicos()["items"][0]["imagen_url"]
    assert pub.startswith("/api/v1/catalogo/media/eventos/")


@pytest.mark.unit
@pytest.mark.django_db
def test_actualizar_tipo_color(ctx):
    svc = AdminClientesService(audit=MagicMock())
    row = svc.crear_tipo(ctx, {"nombre": "Mayorista S2", "color": "#111111"})["tipo"]
    out = svc.actualizar_tipo(
        ctx,
        row["id_tipo_cliente"],
        {"nombre": "Mayorista S2", "color": "#222222", "version_fila": row["version_fila"]},
    )
    assert out["tipo"]["color"] == "#222222"


@pytest.mark.unit
@pytest.mark.django_db
def test_api_delete_param_y_panel_resumen():
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="s2.admin@test.local",
        password="Admin#2026demo",
        nombre="S2",
        apellido="Admin",
        documento="100009990288",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-s2"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/auth/panel-resumen").status_code == 200
    marca = Marcas.objects.create(nombre="Borrable S2")
    r = client.delete(f"/api/v1/catalogo/parametros/marcas/{marca.id_marca}/")
    assert r.status_code == 200
    assert client.delete("/api/v1/catalogo/parametros/marcas/9999999/").status_code == 404
    assert client.delete("/api/v1/catalogo/parametros/nope/1/").status_code == 400
    from django.utils import timezone

    ev = client.post(
        "/api/v1/eventos/",
        {
            "tipo": TIPO_PROMOCION,
            "titulo": "Upload",
            "descripcion": "Img",
            "fecha_inicio": timezone.now().isoformat(),
        },
        format="json",
    )
    assert ev.status_code == 201
    eid = ev.json()["evento"]["id_evento"]
    assert client.post(f"/api/v1/eventos/{eid}/imagen/", {}, format="multipart").status_code == 400
    buff = BytesIO()
    Image.new("RGB", (10, 10), "green").save(buff, format="PNG")
    ok = client.post(
        f"/api/v1/eventos/{eid}/imagen/",
        {"imagen": SimpleUploadedFile("ev.png", buff.getvalue(), content_type="image/png")},
        format="multipart",
    )
    assert ok.status_code == 200
    assert ok.json()["imagen_url"].startswith("eventos/")
