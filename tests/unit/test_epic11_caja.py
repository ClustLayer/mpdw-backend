from decimal import Decimal

import pytest

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m08_caja.admin_caja_service import AdminCajaService
from apps.m08_caja.caja_epic11_service import CajaEpic11Service, _dec, enmascarar_numero
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
    with pytest.raises(ReglaNegocioError):
        _dec("no-num")
    with pytest.raises(ReglaNegocioError):
        _dec(0)


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
    cat_a = Categorias_movimiento.objects.create(nombre="Ahorro", tipo_movimiento="Ahorro", estado=True)
    ah = svc.registrar_gasto_o_ahorro(
        ctx,
        {"id_sede": sede.id_sede, "tipo": "ahorro", "id_categoria": cat_a.id_categoria_movimiento, "valor": "100", "descripcion": "c"},
    )
    from apps.m08_caja.models import Ahorros

    a = Ahorros.objects.get(pk=ah["id"])
    svc.corregir_movimiento(ctx, "ahorro", a.id_ahorro, {"version_fila": 1, "valor": "150"})


@pytest.mark.unit
@pytest.mark.django_db
def test_movimientos_adicion_entrega_y_ahorro(ctx: AuthContext, sede: Sedes):
    svc = CajaEpic11Service()
    svc.base_inicial_primera(ctx, sede.id_sede, "200000")
    cat_g = Categorias_movimiento.objects.create(nombre="Gasto", tipo_movimiento="Gasto", estado=True)
    cat_a = Categorias_movimiento.objects.create(nombre="Ahorro", tipo_movimiento="Ahorro", estado=True)
    svc.registrar_gasto_o_ahorro(
        ctx,
        {"id_sede": sede.id_sede, "tipo": "ahorro", "id_categoria": cat_a.id_categoria_movimiento, "valor": "1500", "descripcion": "Caja fuerte"},
    )
    assert svc.listar_gastos_ahorros(ctx, sede.id_sede)["ahorros"]
    svc.registrar_adicion(ctx, {"id_sede": sede.id_sede, "valor": "10000", "motivo": "Refuerzo"})
    svc.registrar_entrega(ctx, {"id_sede": sede.id_sede, "valor": "2000", "descripcion": "Vuelto"})
    with pytest.raises(ReglaNegocioError):
        svc.registrar_entrega(ctx, {"id_sede": sede.id_sede, "valor": "-100", "descripcion": "Inválido"})
    assert svc.jornada_actual(ctx, sede.id_sede)["reporte"]["estado"] == "ABIERTO"
    assert svc.registrar_adjunto_stub(ctx, {"tipo_movimiento": "gasto", "id_movimiento": 1})["mensaje"]
    with pytest.raises(ReglaNegocioError):
        svc.registrar_transferencia(ctx, {"id_sede": sede.id_sede, "id_categoria": cat_g.id_categoria_movimiento, "valor": "1"})


@pytest.mark.unit
@pytest.mark.django_db
def test_apertura_export_xlsx_y_cuentas(ctx: AuthContext, sede: Sedes):
    svc = CajaEpic11Service()
    svc.base_inicial_primera(ctx, sede.id_sede, "300000")
    AdminCajaService().crear(
        ctx,
        {"nombre": "Mask Test", "tipo_cuenta": "Nequi", "numero": "3004445566", "estado": True},
    )
    nombre, datos, mime = svc.exportar_historial(ctx, sede.id_sede, "xlsx")
    assert nombre.endswith(".xlsx") and datos and "spreadsheet" in mime
    assert svc.listar_cuentas_enmascaradas(q="", estado=None, page=1, page_size=10)["items"]


@pytest.mark.unit
@pytest.mark.django_db
def test_corregir_movimiento_tipo_invalido(ctx: AuthContext):
    with pytest.raises(ReglaNegocioError):
        CajaEpic11Service().corregir_movimiento(ctx, "desconocido", 1, {"version_fila": 1})


@pytest.mark.unit
@pytest.mark.django_db
def test_historial_vacio_no_exporta(ctx: AuthContext):
    otra = Sedes.objects.create(nombre="Sede vacía", direccion="N/A", estado=True)
    svc = CajaEpic11Service()
    assert svc.historial(ctx, otra.id_sede, None, None)["items"] == []
    assert svc.listar_gastos_ahorros(ctx, otra.id_sede)["gastos"] == []
    assert svc.listar_transferencias(ctx, otra.id_sede)["items"] == []
    assert svc.jornada_actual(ctx, otra.id_sede)["reporte"] is None
    with pytest.raises(ReglaNegocioError):
        svc.exportar_historial(ctx, otra.id_sede, "csv")


@pytest.mark.unit
@pytest.mark.django_db
def test_categoria_concepto_validaciones(ctx: AuthContext, sede: Sedes):
    svc = CajaEpic11Service()
    with pytest.raises(ReglaNegocioError):
        svc.crear_categoria(ctx, {"nombre": "", "tipo_movimiento": "Gasto"})
    cat = svc.crear_categoria(ctx, {"nombre": "Tmp", "tipo_movimiento": "Gasto"})
    pk = cat["item"]["id_categoria_movimiento"]
    with pytest.raises(ReglaNegocioError):
        svc.actualizar_categoria(ctx, 99999, {"nombre": "x", "version_fila": 1})
    svc.actualizar_categoria(ctx, pk, {"nombre": "Tmp", "tipo_movimiento": "Gasto", "version_fila": 1, "estado": False})
    assert svc.listar_conceptos("Gasto", "tax")["items"] == []
    with pytest.raises(ReglaNegocioError):
        svc.crear_concepto(ctx, {"nombre": "Huérfano", "id_categoria": 99999, "valor_sugerido": "1"})
    s2 = Sedes.objects.create(nombre="S2 valid", direccion="B", estado=True)
    svc.base_inicial_primera(ctx, s2.id_sede, "1")
    with pytest.raises(ReglaNegocioError):
        svc.base_inicial_primera(ctx, s2.id_sede, "2")
    svc.base_inicial_primera(ctx, sede.id_sede, "90000")
    rep = Reportes_diarios.objects.get(id_sede=sede, estado="ABIERTO")
    with pytest.raises(ReglaNegocioError):
        svc.reapertura_jornada(ctx, sede.id_sede, {"id_reporte_diario": rep.id_reporte_diario, "version_fila": 99})
