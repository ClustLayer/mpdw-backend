from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m06_ventas.admin_facturacion_externa_service import AdminFacturacionExternaService
from apps.m06_ventas.mensajes_fe import MSG_BANDEJA_VACIA, MSG_SOPORTE_NO
from apps.m06_ventas.models import Facturas, Facturas_electronicas, Tipos_venta
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="fe.epic10@test.local",
        password="Admin#2026demo",
        nombre="Fe",
        apellido="Epic10",
        documento="100009990410",
        id_rol=rol,
    )
    return AuthContext(user.id_usuario, user.email, "Administrador", (), True, id_rol=rol.id_rol, ip="127.0.0.1")


@pytest.fixture
def factura_fe(ctx: AuthContext) -> tuple[Facturas, Facturas_electronicas]:
    sede = Sedes.objects.create(nombre="Sede FE", direccion="Calle", estado=True, ciudad="BOG")
    tipo, _ = Tipos_venta.objects.get_or_create(nombre="Mostrador", defaults={"estado": True})
    user = Usuarios.objects.get(pk=ctx.id_usuario)
    f = Facturas.objects.create(
        id_sede=sede,
        serie="FE",
        numero_factura="1001",
        id_usuario=user,
        id_tipo_venta=tipo,
        subtotal=Decimal("50000"),
        total=Decimal("50000"),
        estado="EMITIDA",
        requiere_factura_electronica=True,
        comprador_nombre="Cliente FE",
    )
    fe = Facturas_electronicas.objects.create(id_factura=f, estado="PENDIENTE")
    return f, fe


@pytest.mark.unit
@pytest.mark.django_db
def test_bandeja_y_detalle(ctx: AuthContext, factura_fe: tuple[Facturas, Facturas_electronicas]) -> None:
    svc = AdminFacturacionExternaService(audit=MagicMock())
    vacia = svc.bandeja("CANCELADA", None, None, None, 1, 10)
    assert vacia["mensaje"] == MSG_BANDEJA_VACIA
    out = svc.bandeja(None, None, None, "1001", 1, 10)
    assert out["total"] == 1
    assert "Mostrando" in out["mensaje"]
    _, fe = factura_fe
    det = svc.detalle(fe.id_factura_electronica)
    assert det["item"]["numero_factura"].endswith("1001")
    assert "url_pdf" not in det["item"]


@pytest.mark.unit
@pytest.mark.django_db
def test_generar_externa_y_soporte(ctx: AuthContext, factura_fe: tuple[Facturas, Facturas_electronicas]) -> None:
    svc = AdminFacturacionExternaService(audit=MagicMock())
    _, fe = factura_fe
    out = svc.actualizar_estado(
        ctx,
        fe.id_factura_electronica,
        {
            "estado": "GENERADA_EXTERNA",
            "numero_electronico": "EXT-554433",
            "url_pdf": "https://proveedor.test/fe/554433.pdf",
            "version_fila": fe.version_fila,
        },
    )
    assert out["item"]["estado"] == "GENERADA_EXTERNA"
    assert out["item"]["numero_electronico"] == "EXT-554433"
    url = svc.url_soporte(fe.id_factura_electronica)
    assert url["url_pdf"].startswith("https://")


@pytest.mark.unit
@pytest.mark.django_db
def test_soporte_bloqueado_si_pendiente(factura_fe: tuple[Facturas, Facturas_electronicas]) -> None:
    svc = AdminFacturacionExternaService()
    _, fe = factura_fe
    with pytest.raises(ReglaNegocioError) as err:
        svc.url_soporte(fe.id_factura_electronica)
    assert err.value.mensaje == MSG_SOPORTE_NO


@pytest.mark.unit
@pytest.mark.django_db
def test_validaciones_estado(ctx: AuthContext, factura_fe: tuple[Facturas, Facturas_electronicas]) -> None:
    svc = AdminFacturacionExternaService(audit=MagicMock())
    _, fe = factura_fe
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_estado(
            ctx,
            fe.id_factura_electronica,
            {"estado": "GENERADA_EXTERNA", "numero_electronico": "", "version_fila": fe.version_fila},
        )
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_estado(ctx, fe.id_factura_electronica, {"estado": "CANCELADA", "version_fila": 99})
    cancel = svc.actualizar_estado(
        ctx,
        fe.id_factura_electronica,
        {"estado": "CANCELADA", "version_fila": fe.version_fila, "observaciones": "Anulada"},
    )
    assert cancel["item"]["estado"] == "CANCELADA"


@pytest.mark.unit
@pytest.mark.django_db
def test_url_invalida_y_auditoria(ctx: AuthContext, factura_fe: tuple[Facturas, Facturas_electronicas]) -> None:
    from apps.m10_auditoria.models import Auditoria

    svc = AdminFacturacionExternaService()
    _, fe = factura_fe
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_estado(
            ctx,
            fe.id_factura_electronica,
            {
                "estado": "GENERADA_EXTERNA",
                "numero_electronico": "X",
                "url_pdf": "no-url",
                "version_fila": fe.version_fila,
            },
        )
    svc = AdminFacturacionExternaService()
    svc.actualizar_estado(
        ctx,
        fe.id_factura_electronica,
        {
            "estado": "GENERADA_EXTERNA",
            "numero_electronico": "OK-1",
            "url_pdf": "https://x.test/a.pdf",
            "version_fila": fe.version_fila,
        },
    )
    # Trazabilidad de negocio ya no persiste en Auditoria SQL (E13 → Mongo general_logs).
    assert not Auditoria.objects.filter(accion__icontains="FACTURA").exists()
    with pytest.raises(ReglaNegocioError):
        svc.detalle(99999999)


@pytest.mark.unit
@pytest.mark.django_db
def test_bandeja_filtros_fecha(ctx: AuthContext, factura_fe: tuple[Facturas, Facturas_electronicas]) -> None:
    from django.utils import timezone

    svc = AdminFacturacionExternaService()
    hoy = timezone.localdate().isoformat()
    out = svc.bandeja("PENDIENTE", hoy, hoy, "FE", 1, 10)
    assert out["total"] >= 1
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_estado(ctx, 1, {"estado": "", "version_fila": 1})
    _, fe = factura_fe
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_estado(
            ctx,
            fe.id_factura_electronica,
            {"estado": "GENERADA_EXTERNA", "numero_electronico": "x" * 101, "version_fila": fe.version_fila},
        )
    fantasma = AuthContext(999999, "x@test", "Administrador", (), True)
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_estado(fantasma, fe.id_factura_electronica, {"estado": "CANCELADA", "version_fila": fe.version_fila})
    svc2 = AdminFacturacionExternaService()
    svc2.actualizar_estado(
        ctx,
        fe.id_factura_electronica,
        {"estado": "GENERADA_EXTERNA", "numero_electronico": "SIN-PDF", "version_fila": fe.version_fila},
    )
    with pytest.raises(ReglaNegocioError):
        svc2.url_soporte(fe.id_factura_electronica)
