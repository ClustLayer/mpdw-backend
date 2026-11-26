import pytest

from apps.m10_auditoria.models import Auditoria
from apps.m10_auditoria.services import AuditService
from apps.m13_plataforma.observability import general_log_writer as glw
from apps.m13_plataforma.observability.fake_mongo_store import FakeMongoStore
from contratos.dtos import AuditoriaDTO


@pytest.mark.unit
@pytest.mark.django_db
def test_registrar_seguridad_en_sql():
    AuditService().registrar(
        AuditoriaDTO(
            id_usuario=None,
            accion="LOGIN_EXITOSO",
            entidad="Usuarios",
            id_entidad=0,
            motivo="ok",
        )
    )
    assert Auditoria.objects.filter(accion="LOGIN_EXITOSO").count() == 1


@pytest.mark.unit
@pytest.mark.django_db
def test_registrar_negocio_en_mongo_fake(monkeypatch):
    store = FakeMongoStore()
    writer = glw.GeneralLogWriter(store)
    monkeypatch.setattr(glw, "_writer", writer)
    AuditService().registrar(
        AuditoriaDTO(
            id_usuario=2,
            accion="CREAR_PRODUCTO",
            entidad="Productos",
            id_entidad=9,
            motivo="alta",
            datos_despues={"nombre": "X"},
        )
    )
    import time

    time.sleep(0.5)
    assert Auditoria.objects.count() == 0
    assert store.documents.get("general_logs")
    assert store.documents["general_logs"][0]["accion"] == "CREAR_PRODUCTO"
    writer.log_http(metodo="GET", ruta="/api/v1/x", status=200, correlation_id="c1", ms=12.5)
    time.sleep(0.3)
    writer.shutdown()
    assert any(d.get("tipo") == "http_request" for d in store.documents.get("general_logs", []))


@pytest.mark.unit
def test_fake_mongo_insert_one_y_build_store(monkeypatch):
    from apps.m13_plataforma.observability import mongo_client as mc
    from apps.m13_plataforma.observability.fake_mongo_store import FakeMongoStore

    store = FakeMongoStore()
    store.insert_one("c", {"a": 1})
    store.insert_many("c", [])
    assert store.documents["c"][0]["a"] == 1
    monkeypatch.setattr(mc.settings, "MPDW_OBSERVABILITY_FAKE_MONGO", True)
    assert mc.build_store("MONGODB_GENERAL_URI") is not None
    monkeypatch.setattr(mc.settings, "MPDW_OBSERVABILITY_FAKE_MONGO", False)
    monkeypatch.delenv("MONGODB_GENERAL_URI", raising=False)
    monkeypatch.setattr(mc.settings, "MONGODB_GENERAL_URI", "", raising=False)
    assert mc.build_store("MONGODB_GENERAL_URI") is None
    from apps.m13_plataforma.observability.migration_backup import _accion_sql

    assert _accion_sql("LOGIN_EXITOSO") is True
    assert _accion_sql("CREAR_X") is False
