from decimal import Decimal

import pytest

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m08_caja.admin_caja_service import AdminCajaService
from apps.m08_caja.caja_epic11_service import CajaEpic11Service, enmascarar_numero
from apps.m08_caja.models import (
    Categorias_movimiento,
    Cuentas_bancarias,
    Gastos_caja,
    Reportes_diarios,
    Transferencias_caja,
)
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def sede(db) -> Sedes:
    return Sedes.objects.create(nombre="Sede Caja", direccion="Calle 1", estado=True)


@pytest.fixture
def ctx(db, sede: Sedes) -> AuthContext:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="epic11.caja@test.local",
        password="Admin#2026demo",
        nombre="Caja",
        apellido="Epic11",
        documento="1000111101",
        id_rol=rol,
    )
    return AuthContext(user.id_usuario, user.email, "Administrador", (sede.id_sede,), True, id_rol=rol.id_rol, ip="127.0.0.1")


@pytest.mark.unit
def test_enmascarar_numero():
    assert enmascarar_numero("3001234567").endswith("4567")
    assert "*" in enmascarar_numero("3001234567")
    assert enmascarar_numero("12") == "****"


@pytest.mark.unit
@pytest.mark.django_db
def test_categorias_conceptos_crud(ctx: AuthContext):
    svc = CajaEpic11Service()
    cat = svc.crear_categoria(ctx, {"nombre": "Transporte", "tipo_movimiento": "Gasto"})
    assert "creada" in cat["mensaje"].lower()
    pk = cat["item"]["id_categoria_movimiento"]
    act = svc.actualizar_categoria(
        ctx, pk, {"nombre": "Transporte", "tipo_movimiento": "Gasto", "version_fila": 1}
    )
    assert act["item"]["nombre"] == "Transporte"
    con = svc.crear_concepto(ctx, {"nombre": "Taxi", "id_categoria": pk, "valor_sugerido": "15000"})
    cid = con["item"]["id_concepto_movimiento"]
    svc.actualizar_concepto(ctx, cid, {"nombre": "Taxi sede", "version_fila": 1})
    assert svc.listar_conceptos("Gasto", "")["items"]


@pytest.mark.unit
@pytest.mark.django_db
def test_jornada_movimientos_y_cierre(ctx: AuthContext, sede: Sedes):
    svc = CajaEpic11Service()
    svc.base_inicial_primera(ctx, sede.id_sede, "500000")
    cat_g = Categorias_movimiento.objects.create(nombre="Operación", tipo_movimiento="Gasto", estado=True)
    cat_t = Categorias_movimiento.objects.create(nombre="Nequi", tipo_movimiento="Transferencia", estado=True)
    cuenta = Cuentas_bancarias.objects.create(nombre="Titular Nequi", banco="Nequi", tipo_cuenta="Nequi", numero="3009998877")
    svc.registrar_gasto_o_ahorro(
        ctx,
        {"id_sede": sede.id_sede, "tipo": "gasto", "id_categoria": cat_g.id_categoria_movimiento, "valor": "10000", "descripcion": "Café"},
    )
    svc.registrar_transferencia(
        ctx,
        {
            "id_sede": sede.id_sede,
            "id_categoria": cat_t.id_categoria_movimiento,
            "id_cuenta_bancaria": cuenta.id_cuenta_bancaria,
            "valor": "20000",
            "referencia": "TRF-1",
        },
    )
    cuadre = svc.cuadre_tiempo_real(ctx, sede.id_sede)
    assert cuadre["reporte"]["efectivo_esperado"] is not None
    rep = Reportes_diarios.objects.get(id_sede=sede, estado="ABIERTO")
    cierre = svc.cierre_jornada(
        ctx,
        sede.id_sede,
        {"efectivo_declarado": cuadre["reporte"]["efectivo_esperado"], "version_fila": rep.version_fila, "base_siguiente": "500000"},
    )
    assert cierre["reporte"]["estado"] == "CERRADO"
    reap = svc.reapertura_jornada(
        ctx,
        sede.id_sede,
        {"id_reporte_diario": rep.id_reporte_diario, "version_fila": cierre["reporte"]["version_fila"]},
    )
    assert reap["reporte"]["estado"] == "ABIERTO"


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_cuentas_enmascara(ctx: AuthContext):
    AdminCajaService().crear(
        ctx,
        {"nombre": "Titular Test", "tipo_cuenta": "Nequi", "numero": "3001112233", "estado": True},
    )
    lista = AdminCajaService().listar("", None, 1, 20)
    assert any("*" in it["numero"] for it in lista["items"])


@pytest.mark.unit
@pytest.mark.django_db
def test_transferencia_facturada_no_editable(ctx: AuthContext, sede: Sedes):
    svc = CajaEpic11Service()
    if not Reportes_diarios.objects.filter(id_sede=sede, estado="ABIERTO").exists():
        svc.base_inicial_primera(ctx, sede.id_sede, "100000")
    rep = Reportes_diarios.objects.get(id_sede=sede, estado="ABIERTO")
    cat = Categorias_movimiento.objects.create(nombre="Venta", tipo_movimiento="Transferencia", estado=True)
    cuenta = Cuentas_bancarias.objects.first()
    assert cuenta is not None
    t = Transferencias_caja.objects.create(
        id_reporte_diario=rep,
        id_categoria=cat,
        id_cuenta_bancaria=cuenta,
        valor=Decimal("5000"),
        referencia="FAC-1",
        origen="VENTA",
        editable=False,
        id_usuario_id=ctx.id_usuario,
    )
    with pytest.raises(ReglaNegocioError) as exc:
        svc.corregir_movimiento(ctx, "transferencia", t.id_transferencia, {"version_fila": 1, "valor": "6000"})
    assert exc.value.codigo == "TRANSFERENCIA_FACTURADA"


@pytest.mark.unit
@pytest.mark.django_db
def test_historial_export(ctx: AuthContext, sede: Sedes):
    svc = CajaEpic11Service()
    svc.base_inicial_primera(ctx, sede.id_sede, "100000")
    hist = svc.historial(ctx, sede.id_sede, None, None)
    assert hist["items"]
    nombre, datos, mime = svc.exportar_historial(ctx, sede.id_sede, "csv")
    assert nombre.endswith(".csv")
    assert datos and mime == "text/csv"


@pytest.mark.unit
@pytest.mark.django_db
def test_anular_gasto(ctx: AuthContext, sede: Sedes):
    svc = CajaEpic11Service()
    svc.base_inicial_primera(ctx, sede.id_sede, "100000")
    cat = Categorias_movimiento.objects.create(nombre="Varios", tipo_movimiento="Gasto", estado=True)
    r = svc.registrar_gasto_o_ahorro(
        ctx, {"id_sede": sede.id_sede, "tipo": "gasto", "id_categoria": cat.id_categoria_movimiento, "valor": "5000", "descripcion": "x"}
    )
    g = Gastos_caja.objects.get(pk=r["id"])
    svc.corregir_movimiento(ctx, "gasto", g.id_gasto, {"version_fila": 1, "anulado": True, "motivo_anulacion": "Error"})
    assert Gastos_caja.objects.get(pk=g.id_gasto).anulado is True