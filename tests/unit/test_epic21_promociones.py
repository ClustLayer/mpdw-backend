import io
from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from PIL import Image

from apps.m13_plataforma.observability.fake_mongo_store import FakeMongoStore
from apps.m13_plataforma.observability.interactions_service import registrar_lote
from apps.m13_plataforma.observability import interactions_service as ix
from apps.m21_promociones.admin_promociones_service import AdminPromocionesService
from apps.m21_promociones.models import ESTADO_ACTIVA, ESTADO_PAUSADA, Promociones
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


def _ctx() -> AuthContext:
    return AuthContext(
        id_usuario=1,
        email="g@test.local",
        rol_nombre="Gerente",
        sedes_asignadas=(1,),
        es_global=True,
    )


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(200, 40, 80)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.unit
@pytest.mark.django_db
def test_publicas_solo_vigentes_con_imagen():
    ahora = timezone.now()
    Promociones.objects.create(
        titulo="Vigente",
        tipo="promocion",
        descripcion="d",
        hashtags="#a",
        imagen="promociones/x.jpg",
        fecha_inicio=ahora - timezone.timedelta(days=1),
        fecha_fin=ahora + timezone.timedelta(days=1),
        estado=ESTADO_ACTIVA,
    )
    Promociones.objects.create(
        titulo="Sin imagen",
        tipo="promocion",
        descripcion="d",
        imagen="",
        fecha_inicio=ahora - timezone.timedelta(days=1),
        estado=ESTADO_ACTIVA,
    )
    Promociones.objects.create(
        titulo="Pausada",
        tipo="sorteo",
        descripcion="d",
        imagen="promociones/y.jpg",
        fecha_inicio=ahora - timezone.timedelta(days=1),
        fecha_fin=ahora + timezone.timedelta(days=1),
        estado=ESTADO_PAUSADA,
    )
    data = AdminPromocionesService().publicas()
    assert len(data["items"]) == 1
    assert data["items"][0]["titulo"] == "Vigente"


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_listar_actualizar_y_fechas():
    inicio = timezone.now()
    svc = AdminPromocionesService(audit=MagicMock())
    r = svc.crear(
        _ctx(),
        {
            "titulo": "Sorteo",
            "tipo": "sorteo",
            "descripcion": "Texto",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": (inicio + timezone.timedelta(days=3)).isoformat(),
            "hashtags": "#sorteo",
        },
    )
    assert r["promocion"]["tipo"] == "sorteo"
    pk = r["promocion"]["id_promocion"]
    assert svc.listar("Sorteo", "activa", 1, 10)["total"] == 1
    assert svc.obtener(pk)["titulo"] == "Sorteo"
    with pytest.raises(ReglaNegocioError):
        svc.crear(_ctx(), {"titulo": "X", "tipo": "otro", "descripcion": "d", "fecha_inicio": inicio.isoformat()})
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            _ctx(),
            {
                "titulo": "Bad",
                "tipo": "promocion",
                "descripcion": "d",
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": (inicio - timezone.timedelta(days=1)).isoformat(),
            },
        )
    act = svc.actualizar(
        _ctx(),
        pk,
        {
            "titulo": "Sorteo 2",
            "tipo": "sorteo",
            "descripcion": "Texto",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": (inicio + timezone.timedelta(days=5)).isoformat(),
            "estado": "pausada",
            "version_fila": 1,
        },
    )
    assert act["promocion"]["titulo"] == "Sorteo 2"
    with pytest.raises(ReglaNegocioError):
        svc.actualizar(_ctx(), pk, {**act["promocion"], "version_fila": 1})


@pytest.mark.unit
@pytest.mark.django_db
def test_guardar_imagen_png():
    inicio = timezone.now()
    svc = AdminPromocionesService(audit=MagicMock())
    r = svc.crear(
        _ctx(),
        {
            "titulo": "Img",
            "tipo": "promocion",
            "descripcion": "d",
            "fecha_inicio": inicio.isoformat(),
        },
    )
    pk = r["promocion"]["id_promocion"]
    rel = svc.guardar_imagen(pk, "a.png", _png_bytes(), "image/png")
    assert rel.startswith("promociones/")
    with pytest.raises(ReglaNegocioError):
        svc.guardar_imagen(pk, "a.gif", b"xx", "image/gif")


@pytest.mark.unit
def test_interacciones_lote_fake(monkeypatch):
    store = FakeMongoStore()
    monkeypatch.setattr(ix, "_store", store)
    out = registrar_lote(
        id_usuario=None,
        eventos=[{"boton": "whatsapp_promo", "pantalla": "home", "id_promocion": 7}],
    )
    assert out["registrados"] == 1
    assert store.documents["interacciones"][0]["id_promocion"] == 7
    assert registrar_lote(id_usuario=1, eventos=[])["registrados"] == 0
    assert registrar_lote(id_usuario=1, eventos=["x"])["registrados"] == 0  # type: ignore[list-item]

    class Boom:
        def insert_many(self, collection, docs):
            raise RuntimeError("down")

    monkeypatch.setattr(ix, "_store", Boom())
    assert registrar_lote(id_usuario=1, eventos=[{"boton": "x", "pantalla": "y"}])["registrados"] == 0
    assert registrar_lote(id_usuario=1, eventos=[{"boton": "z", "pantalla": "p", "id_promocion": "no"}])["registrados"] == 0


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_sin_coincidencias_y_jpeg():
    svc = AdminPromocionesService(audit=MagicMock())
    assert svc.listar("zzz-no-match", "todos", 1, 10)["mensaje"]
    inicio = timezone.now()
    r = svc.crear(
        _ctx(),
        {"titulo": "Jpg", "tipo": "promocion", "descripcion": "d", "fecha_inicio": inicio.isoformat()},
    )
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(1, 2, 3)).save(buf, format="JPEG")
    rel = svc.guardar_imagen(r["promocion"]["id_promocion"], "a.jpg", buf.getvalue(), "image/jpeg")
    assert rel.endswith(".jpg")
    with pytest.raises(Promociones.DoesNotExist):
        svc.obtener(999999)


@pytest.mark.unit
def test_request_logging_middleware(monkeypatch):
    from apps.m13_plataforma.request_logging_middleware import RequestLoggingMiddleware

    called: list[dict] = []

    class W:
        def log_http(self, **kwargs):
            called.append(kwargs)

    monkeypatch.setattr(
        "apps.m13_plataforma.request_logging_middleware.get_general_log_writer",
        lambda: W(),
    )
    monkeypatch.setattr(
        "apps.m13_plataforma.request_logging_middleware.settings",
        type("S", (), {"REQUEST_LOGGING_ENABLED": True})(),
    )
    mw = RequestLoggingMiddleware(lambda r: type("R", (), {"status_code": 204})())
    req = type("Req", (), {"method": "GET", "path": "/x", "correlation_id": "abc"})()
    resp = mw(req)
    assert resp.status_code == 204 and called