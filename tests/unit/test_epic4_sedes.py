"""Unit tests Epic 4 — sedes."""

import pytest

from apps.m02_sedes.admin_sedes_service import AdminSedesService
from apps.m02_sedes.models import Sedes
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx_admin() -> AuthContext:
    return AuthContext(
        id_usuario=1,
        email="admin@test.local",
        rol_nombre="Administrador",
        sedes_asignadas=(1,),
        es_global=True,
        id_rol=1,
        ip="127.0.0.1",
        user_agent="pytest",
        id_correlacion="s1",
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_sede_exito(ctx_admin):
    svc = AdminSedesService(audit_port=__import__("unittest.mock").mock.MagicMock())
    _, msg = svc.crear(
        ctx_admin,
        {
            "nombre": "Sede Norte",
            "direccion": "Calle 1",
            "telefono": "+573001234567",
            "horarios": [{"dia_semana": 1, "hora_apertura": "08:00", "hora_cierre": "17:00"}],
        },
    )
    assert "correctamente" in msg
    assert Sedes.objects.filter(nombre="Sede Norte").exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_sede_campos_obligatorios(ctx_admin):
    svc = AdminSedesService(audit_port=__import__("unittest.mock").mock.MagicMock())
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear(ctx_admin, {"nombre": "", "direccion": "X", "telefono": "+573001234567"})
    assert exc.value.codigo == "CAMPOS_OBLIGATORIOS"


@pytest.mark.unit
@pytest.mark.django_db
def test_editar_y_listar_publicas(ctx_admin):
    mock = __import__("unittest.mock").mock.MagicMock()
    svc = AdminSedesService(audit_port=mock)
    det, _ = svc.crear(
        ctx_admin,
        {"nombre": "Pub", "direccion": "Calle 2", "telefono": "+573001234567"},
    )
    det2, msg = svc.editar(
        ctx_admin,
        det["id_sede"],
        {"nombre": "Pub 2", "direccion": "Calle 2", "telefono": "+573001234567", "version_fila": det["version_fila"]},
    )
    assert "correctamente" in msg
    assert det2["nombre"] == "Pub 2"
    assert any(s["nombre"] == "Pub 2" for s in svc.listar_publicas())


@pytest.mark.unit
@pytest.mark.django_db
def test_consolidado_fechas(ctx_admin):
    from datetime import date

    svc = AdminSedesService(audit_port=__import__("unittest.mock").mock.MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc.consolidado(ctx_admin, None, date(2026, 2, 1), date(2026, 1, 1))
    out = svc.consolidado(ctx_admin, None, date(2026, 1, 1), date(2026, 1, 31))
    assert "mensaje" in out


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_sedes_y_telefono_invalido(ctx_admin):
    mock = __import__("unittest.mock").mock.MagicMock()
    svc = AdminSedesService(audit_port=mock)
    svc.crear(ctx_admin, {"nombre": "L1", "direccion": "D", "telefono": "+573001234567"})
    pag = svc.listar(q="L1", page=1, page_size=10)
    assert pag["total"] >= 1
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear(ctx_admin, {"nombre": "Bad", "direccion": "D", "telefono": "abc"})
    assert exc.value.codigo == "TELEFONO_INVALIDO"


@pytest.mark.unit
@pytest.mark.django_db
def test_horario_cierre_invalido(ctx_admin):
    svc = AdminSedesService(audit_port=__import__("unittest.mock").mock.MagicMock())
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear(
            ctx_admin,
            {
                "nombre": "H",
                "direccion": "D",
                "telefono": "+573001234567",
                "horarios": [
                    {"dia_semana": 1, "hora_apertura": "17:00", "hora_cierre": "08:00", "cerrado": False}
                ],
            },
        )
    assert exc.value.codigo == "HORARIO_INVALIDO"


@pytest.mark.unit
@pytest.mark.django_db
def test_desactivar_con_jornada_abierta(ctx_admin, monkeypatch):
    mock = __import__("unittest.mock").mock.MagicMock()
    svc = AdminSedesService(audit_port=mock)
    det, _ = svc.crear(
        ctx_admin,
        {"nombre": "Jor", "direccion": "D", "telefono": "+573001234567"},
    )
    monkeypatch.setattr(svc._caja, "jornada_esta_abierta", lambda _id: True)
    with pytest.raises(ReglaNegocioError) as exc:
        svc.editar(
            ctx_admin,
            det["id_sede"],
            {
                "nombre": "Jor",
                "direccion": "D",
                "telefono": "+573001234567",
                "estado": False,
                "version_fila": det["version_fila"],
            },
        )
    assert exc.value.codigo == "JORNADA_ABIERTA"


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_filtro_inactivo_y_concurrencia(ctx_admin):
    mock = __import__("unittest.mock").mock.MagicMock()
    svc = AdminSedesService(audit_port=mock)
    det, _ = svc.crear(
        ctx_admin,
        {"nombre": "Inact", "direccion": "D", "telefono": "+573001234567"},
    )
    svc.editar(
        ctx_admin,
        det["id_sede"],
        {
            "nombre": "Inact",
            "direccion": "D",
            "telefono": "+573001234567",
            "estado": False,
            "version_fila": det["version_fila"],
        },
    )
    assert svc.listar(estado="inactivo", page=1, page_size=5)["total"] >= 1
    with pytest.raises(ReglaNegocioError) as exc:
        svc.editar(
            ctx_admin,
            det["id_sede"],
            {
                "nombre": "X",
                "direccion": "D",
                "telefono": "+573001234567",
                "version_fila": 999,
            },
        )
    assert exc.value.codigo == "CONCURRENCIA"


@pytest.mark.unit
@pytest.mark.django_db
def test_whatsapp_invalido_y_sede_inexistente(ctx_admin):
    svc = AdminSedesService(audit_port=__import__("unittest.mock").mock.MagicMock())
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            ctx_admin,
            {
                "nombre": "W",
                "direccion": "D",
                "telefono": "+573001234567",
                "whatsapp": "bad",
            },
        )
    with pytest.raises(Sedes.DoesNotExist):
        svc.editar(
            ctx_admin,
            999_999,
            {"nombre": "X", "direccion": "D", "telefono": "+573001234567", "version_fila": 1},
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_maps_y_texto_horario_publico(ctx_admin):
    mock = __import__("unittest.mock").mock.MagicMock()
    svc = AdminSedesService(audit_port=mock)
    svc.crear(
        ctx_admin,
        {
            "nombre": "Mapa",
            "direccion": "Calle 10",
            "telefono": "+573001234567",
            "maps_url": "https://www.google.com/maps/embed?pb=test",
            "map_query": "Calle 10, Cali",
            "horarios": [
                {"dia_semana": d, "hora_apertura": "08:00", "hora_cierre": "18:00", "cerrado": d == 7}
                for d in range(1, 8)
            ],
        },
    )
    pub = svc.listar_publicas()
    row = next(s for s in pub if s["nombre"] == "Mapa")
    assert row["maps_url"].startswith("https://")
    assert row["map_query"] == "Calle 10, Cali"
    assert row.get("schedule_text")
