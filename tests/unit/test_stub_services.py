# ==============================================================================
# Pruebas Unitarias de Servicios Stub, Manejador de Excepciones y Cobertura - MPDW
# ==============================================================================
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)

from apps.m03_catalogo.models import Productos
from apps.m03_catalogo.services import ProductoService
from apps.m05_clientes.services import ClienteService
from apps.m06_ventas.services import VentaService
from apps.m07_domicilios.services import DomicilioService
from apps.m08_caja.services import (
    VarianteCalculoEfectivo,
    calcular_efectivo_esperado,
)
from apps.m11_eventos.services import EventoService
from apps.m12_tienda_publica.services import PedidoWebService
from apps.m13_plataforma.excepciones import uniform_exception_handler
from apps.m13_plataforma.gestor_transaccion import GestorTransaccionDjango
from contratos.dtos import AuthContext
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
from contratos.puertos import (
    almacenamiento,
    auditoria,
    caja,
    correo,
    inventario,
    sedes,
    transaccion,
    ventas,
)


@pytest.mark.unit
def test_importacion_puertos_contratos():
    assert almacenamiento.FileStoragePort is not None
    assert auditoria.AuditPort is not None
    assert caja.CashPort is not None
    assert correo.EmailPort is not None
    assert inventario.InventoryPort is not None
    assert sedes.SedeReadPort is not None
    assert transaccion.GestorTransaccionPort is not None
    assert ventas.SalesReadPort is not None


@pytest.mark.unit
def test_instanciacion_servicios_stub():
    c_service = ClienteService()
    assert c_service is not None

    v_service = VentaService()
    assert v_service is not None

    d_service = DomicilioService()
    assert d_service is not None

    e_service = EventoService()
    assert e_service is not None

    p_service = PedidoWebService()
    assert p_service is not None


@pytest.mark.unit
def test_reexportacion_servicios_caja():
    assert VarianteCalculoEfectivo.VARIANTE_A == "VARIANTE_A"
    res = calcular_efectivo_esperado(
        base_inicial=Decimal("10.00"),
        base_adicional=Decimal("0.00"),
        ventas=Decimal("20.00"),
        transferencias_a_descontar=Decimal("5.00"),
        gastos=Decimal("2.00"),
        ahorros=Decimal("0.00"),
    )
    assert res == Decimal("23.00")


@pytest.mark.unit
def test_producto_service_sin_gestor_transaccion_cubre_ramas_directas():
    repo_mock = MagicMock()
    precio_mock = MagicMock()
    prod = Productos(id_producto=1, codigo_producto="P1", nombre="P", precio_venta=Decimal("100"), version=1)
    repo_mock.crear_producto.return_value = prod
    repo_mock.buscar_por_codigo.return_value = None
    repo_mock.buscar_por_id.return_value = prod
    repo_mock.actualizar_precio_concurrente.return_value = 1

    service = ProductoService(
        producto_repo=repo_mock,
        precio_repo=precio_mock,
        tx_manager=None,  # Sin gestor de transacción para cubrir líneas directas 115 y 189
    )

    ctx = AuthContext(id_usuario=1, email="a@d.com", rol_nombre="Admin", sedes_asignadas=(1,), es_global=True)
    p_creado = service.crear_producto(
        ctx=ctx,
        codigo_producto="P1",
        codigo_barras=None,
        nombre="P",
        descripcion="",
        precio_venta=Decimal("100"),
        id_categoria=1,
    )
    assert p_creado.id_producto == 1

    p_actualizado = service.cambiar_precio(
        ctx=ctx,
        id_producto=1,
        nuevo_precio=Decimal("150"),
        version=1,
        motivo="Ajuste anual",
    )
    assert p_actualizado.precio_venta == Decimal("150")


@pytest.mark.unit
def test_gestor_transaccion_django_mock_atomic():
    with patch("django.db.transaction.atomic") as mock_atomic:
        mock_atomic.return_value.__enter__.return_value = None
        gestor = GestorTransaccionDjango()
        ejecutado = False
        with gestor.atomic():
            ejecutado = True
        assert ejecutado is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "excepcion,status_esperado,codigo_esperado",
    [
        (ConflictoVersionError("Version vieja"), 409, "CONFLICTO_CONCURRENCIA"),
        (StockInsuficienteError("Sin stock"), 409, "STOCK_INSUFICIENTE"),
        (SedeNoAutorizadaError("Sede no asignada"), 403, "SEDE_NO_AUTORIZADA"),
        (PermisoDenegadoError("Sin permiso"), 403, "PERMISO_DENEGADO"),
        (PermissionDenied("Denegado"), 403, "ACCESO_DENEGADO"),
        (AutenticacionError("No auth"), 401, "NO_AUTENTICADO"),
        (AuthenticationFailed("Token invalido"), 401, "NO_AUTENTICADO"),
        (NotAuthenticated("Falta token"), 401, "NO_AUTENTICADO"),
        (RecursoNoEncontradoError("No existe"), 404, "NO_ENCONTRADO"),
        (NotFound("No encontrado"), 404, "NO_ENCONTRADO"),
        (ReglaNegocioError("Violacion regla"), 422, "REGLA_NEGOCIO_VIOLADA"),
        (ValidationError({"campo": ["invalido"]}), 400, "DATOS_INVALIDOS"),
        (ValidationError("Error simple"), 400, "DATOS_INVALIDOS"),
        (Throttled(wait=30), 429, "LIMITE_TASA_EXCEDIDO"),
        (DominioError("Error general dominio"), 400, "ERROR_DOMINIO"),
        (Exception("Crash inesperado"), 500, "ERROR_INTERNO"),
    ],
)
def test_uniform_exception_handler_todas_las_ramas(excepcion, status_esperado, codigo_esperado):
    request_mock = MagicMock()
    request_mock.correlation_id = "test-corr-id"
    context = {"request": request_mock}

    response = uniform_exception_handler(excepcion, context)
    assert response is not None
    assert response.status_code == status_esperado
    assert response.data["codigo"] == codigo_esperado
    assert response.data["idCorrelacion"] == "test-corr-id"


@pytest.mark.unit
def test_uniform_exception_handler_modo_debug():
    with override_settings(DEBUG=True):
        request_mock = MagicMock()
        request_mock.correlation_id = "debug-corr-id"
        context = {"request": request_mock}
        response = uniform_exception_handler(Exception("Detalle tecnico sensible"), context)
        assert response is not None
        assert response.status_code == 500
        assert "Detalle tecnico sensible" in response.data["detalles"]


@pytest.mark.unit
def test_contratos_excepciones_constructores_y_defaults():
    e1 = ConflictoVersionError()
    assert e1.codigo == "CONFLICTO_CONCURRENCIA"
    assert e1.detalles == []

    e2 = StockInsuficienteError()
    assert e2.codigo == "STOCK_INSUFICIENTE"
    assert e2.detalles == []

    e3 = RecursoNoEncontradoError()
    assert e3.codigo == "NO_ENCONTRADO"

    e4 = SedeNoAutorizadaError()
    assert e4.codigo == "SEDE_NO_AUTORIZADA"

    e5 = AutenticacionError()
    assert e5.codigo == "NO_AUTENTICADO"

    e6 = PermisoDenegadoError()
    assert e6.codigo == "PERMISO_DENEGADO"
