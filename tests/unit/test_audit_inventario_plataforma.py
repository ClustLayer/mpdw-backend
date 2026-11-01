# ==============================================================================
# Pruebas Unitarias de Auditoría, Inventario, Transacciones e Idempotencia - MPDW
# SAD Ref: M04, M10, M13, ADR-005, ADR-008
# ==============================================================================
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.m04_inventario.services import InventarioService
from apps.m10_auditoria.services import AuditService
from apps.m13_plataforma.gestor_transaccion import GestorTransaccionDjango
from apps.m13_plataforma.idempotencia import IdempotencyHelper
from contratos.dtos import AuditoriaDTO, StockInicialDTO
from contratos.excepciones import (
    AutenticacionError,
    ConflictoVersionError,
    DominioError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    ReglaNegocioError,
    SedeNoAutorizadaError,
    StockInsuficienteError,
)


@pytest.mark.unit
def test_audit_service_delega_en_repositorio():
    repo_mock = MagicMock()
    service = AuditService(repository=repo_mock)

    dto = AuditoriaDTO(
        id_usuario=1,
        accion="PRUEBA",
        entidad="Productos",
        id_entidad=10,
        datos_antes=None,
        datos_despues={"test": "data"},
        motivo="Prueba unitaria",
    )
    service.registrar(dto)

    repo_mock.insertar.assert_called_once_with(dto)


@pytest.mark.unit
def test_inventario_service_inicializar_stock_con_movimiento():
    inv_repo_mock = MagicMock()
    mov_repo_mock = MagicMock()
    mock_inv = MagicMock()
    mock_inv.id_inventario = 55
    inv_repo_mock.obtener_o_crear.return_value = mock_inv

    service = InventarioService(inv_repo=inv_repo_mock, mov_repo=mov_repo_mock)
    stocks = [StockInicialDTO(id_sede=1, cantidad_inicial=Decimal("10.00"))]

    service.inicializar_stock_producto(id_producto=10, stocks=stocks, motivo="Alta inicial")

    inv_repo_mock.obtener_o_crear.assert_called_once_with(
        id_producto=10, id_sede=1, cantidad_inicial=Decimal("10.00")
    )
    mov_repo_mock.registrar_movimiento.assert_called_once()


@pytest.mark.unit
def test_inventario_service_inicializar_stock_cero_sin_movimiento():
    inv_repo_mock = MagicMock()
    mov_repo_mock = MagicMock()
    mock_inv = MagicMock()
    mock_inv.id_inventario = 56
    inv_repo_mock.obtener_o_crear.return_value = mock_inv

    service = InventarioService(inv_repo=inv_repo_mock, mov_repo=mov_repo_mock)
    stocks = [StockInicialDTO(id_sede=1, cantidad_inicial=Decimal("0.00"))]

    service.inicializar_stock_producto(id_producto=10, stocks=stocks, motivo="Alta inicial")

    inv_repo_mock.obtener_o_crear.assert_called_once_with(
        id_producto=10, id_sede=1, cantidad_inicial=Decimal("0.00")
    )
    mov_repo_mock.registrar_movimiento.assert_not_called()


@pytest.mark.unit
def test_inventario_service_consultar_disponibilidad():
    inv_repo_mock = MagicMock()
    mov_repo_mock = MagicMock()
    inv_repo_mock.consultar_stock.return_value = Decimal("42.00")

    service = InventarioService(inv_repo=inv_repo_mock, mov_repo=mov_repo_mock)
    resultado = service.consultar_disponibilidad(id_producto=10, id_sede=2)

    assert resultado == Decimal("42.00")
    assert service.consultar_stock(10, 2) == Decimal("42.00")
    inv_repo_mock.consultar_stock.assert_called_with(10, 2)


@pytest.mark.unit
def test_gestor_transaccion_django_bloque_atomic():
    with patch("django.db.transaction.atomic") as mock_atomic:
        mock_atomic.return_value.__enter__.return_value = None
        gestor = GestorTransaccionDjango()
        ejecutado = False
        with gestor.atomic():
            ejecutado = True
        assert ejecutado is True


@pytest.mark.unit
def test_idempotency_helper_extrae_de_headers():
    request = MagicMock()
    request.headers = {"Idempotency-Key": "   key-abc-123   "}
    request.data = {}

    clave = IdempotencyHelper.obtener_clave(request)
    assert clave == "key-abc-123"


@pytest.mark.unit
def test_idempotency_helper_extrae_de_body():
    request = MagicMock()
    request.headers = {}
    request.data = {"clave_idempotencia": "body-key-456"}

    clave = IdempotencyHelper.obtener_clave(request)
    assert clave == "body-key-456"


@pytest.mark.unit
def test_idempotency_helper_retorna_none_cuando_no_existe():
    request = MagicMock()
    request.headers = {}
    request.data = {"otro_campo": 123}

    clave = IdempotencyHelper.obtener_clave(request)
    assert clave is None


@pytest.mark.unit
def test_excepciones_dominio_codigos_y_mensajes():
    e1 = ConflictoVersionError(mensaje="Conflicto de version detectado", codigo="CONFLICTO_CONCURRENCIA")
    assert e1.codigo == "CONFLICTO_CONCURRENCIA"
    assert "conflicto" in e1.mensaje.lower()

    e2 = StockInsuficienteError(mensaje="Stock insuficiente")
    assert e2.codigo == "STOCK_INSUFICIENTE"

    e3 = SedeNoAutorizadaError("Sede no permitida")
    assert e3.codigo == "SEDE_NO_AUTORIZADA"

    e4 = PermisoDenegadoError("Permiso denegado")
    assert e4.codigo == "PERMISO_DENEGADO"

    e5 = AutenticacionError("Auth fallida")
    assert e5.codigo == "NO_AUTENTICADO"

    e6 = RecursoNoEncontradoError("No encontrado")
    assert e6.codigo == "NO_ENCONTRADO"

    e7 = ReglaNegocioError("Regla rota")
    assert e7.codigo == "REGLA_NEGOCIO_VIOLADA"

    assert issubclass(ConflictoVersionError, DominioError)


@pytest.mark.unit
def test_sede_service_delega_en_repositorio():
    from apps.m02_sedes.services import SedeService
    repo_mock = MagicMock()
    repo_mock.listar_activas.return_value = ["Sede Norte", "Sede Centro"]

    service = SedeService(repo=repo_mock)
    sedes = service.listar_sedes()
    assert sedes == ["Sede Norte", "Sede Centro"]
    repo_mock.listar_activas.assert_called_once()


@pytest.mark.unit
def test_analitica_service_delega_en_repositorio():
    from apps.m09_analitica.services import AnaliticaService
    repo_mock = MagicMock()
    repo_mock.obtener_resumen_ventas_diarias.return_value = [{"total": 1000}]

    service = AnaliticaService(repo=repo_mock)
    res = service.obtener_ventas()
    assert res == [{"total": 1000}]
    repo_mock.obtener_resumen_ventas_diarias.assert_called_once()


@pytest.mark.unit
def test_stock_inicial_dto_atributos():
    dto = StockInicialDTO(id_sede=3, cantidad_inicial=Decimal("50.00"))
    assert dto.id_sede == 3
    assert dto.cantidad_inicial == Decimal("50.00")
