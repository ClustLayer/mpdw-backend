# ==============================================================================
# Pruebas Unitarias Puras: Servicio de Productos - MPDW
# SAD Ref: M03, TX-06, TX-07, TX-11, RI-02, RI-26, Regla R3
# ==============================================================================
from decimal import Decimal

import pytest

from apps.m03_catalogo.models import Productos
from apps.m03_catalogo.services import ProductoService
from contratos.dtos import StockInicialDTO
from contratos.excepciones import (
    ConflictoVersionError,
    RecursoNoEncontradoError,
    ReglaNegocioError,
)
from tests.conftest import FakeAuditPort, FakeInventoryPort, FakeTransactionManager


class FakeProductoRepo:
    def __init__(self, productos: list[Productos] | None = None) -> None:
        self.productos = {p.id_producto: p for p in (productos or [])}
        self.codigos = {p.codigo_producto: p for p in (productos or [])}

    def buscar_por_id(self, id_producto: int) -> Productos | None:
        return self.productos.get(id_producto)

    def buscar_por_codigo(self, codigo: str) -> Productos | None:
        return self.codigos.get(codigo)

    def listar_con_filtro(self, termino: str | None = None, id_categoria: int | None = None) -> list[Productos]:
        res = list(self.productos.values())
        if termino:
            res = [p for p in res if termino.lower() in p.nombre.lower()]
        return res

    def crear_producto(self, **kwargs) -> Productos:
        p = Productos(
            id_producto=len(self.productos) + 1,
            codigo_producto=kwargs["codigo_producto"],
            codigo_barras=kwargs.get("codigo_barras"),
            nombre=kwargs["nombre"],
            precio_venta=kwargs["precio_venta"],
            version=1,
            estado=True,
        )
        self.productos[p.id_producto] = p
        self.codigos[p.codigo_producto] = p
        return p

    def actualizar_precio_concurrente(self, id_producto: int, nuevo_precio: Decimal, version_esperada: int) -> int:
        p = self.productos.get(id_producto)
        if p and p.version == version_esperada:
            p.precio_venta = nuevo_precio
            p.version += 1
            return 1
        return 0


class FakeHistorialRepo:
    def __init__(self) -> None:
        self.precios: list[dict] = []

    def cerrar_precio_vigente(self, id_producto: int) -> None:
        pass

    def registrar_nuevo_precio(self, id_producto: int, precio_anterior: Decimal, precio_nuevo: Decimal, motivo: str, id_usuario: int | None = None):
        self.precios.append({
            "id_producto": id_producto,
            "anterior": precio_anterior,
            "nuevo": precio_nuevo,
            "motivo": motivo,
        })


@pytest.mark.unit
def test_debe_crear_producto_con_inventario_inicial_y_auditoria(auth_context_admin):
    # Arrange
    prod_repo = FakeProductoRepo()
    hist_repo = FakeHistorialRepo()
    inv_port = FakeInventoryPort()
    audit_port = FakeAuditPort()
    tx_manager = FakeTransactionManager()

    service = ProductoService(
        producto_repo=prod_repo,
        precio_repo=hist_repo,
        inventory_port=inv_port,
        audit_port=audit_port,
        tx_manager=tx_manager,
    )

    stocks = [StockInicialDTO(id_sede=1, cantidad_inicial=Decimal("50.00"))]

    # Act
    producto = service.crear_producto(
        ctx=auth_context_admin,
        codigo_producto="PINT-VINIL-01",
        nombre="Vinilo Tipo 1 Blanco",
        precio_venta=Decimal("45000.00"),
        id_categoria=1,
        stocks_iniciales=stocks,
    )

    # Assert
    assert producto.id_producto == 1
    assert producto.version == 1
    assert len(inv_port.inicializaciones) == 1
    assert len(audit_port.registros) == 1
    assert audit_port.registros[0].accion == "CREAR_PRODUCTO"


@pytest.mark.unit
def test_debe_fallar_creacion_cuando_precio_es_menor_o_igual_a_cero(auth_context_admin):
    # Arrange
    service = ProductoService()

    # Act & Assert
    with pytest.raises(ReglaNegocioError) as exc_info:
        service.crear_producto(
            ctx=auth_context_admin,
            codigo_producto="PINT-02",
            nombre="Brocha",
            precio_venta=Decimal("0.00"),
            id_categoria=1,
        )
    assert "precio de venta debe ser superior a cero" in str(exc_info.value)


@pytest.mark.unit
def test_debe_fallar_creacion_cuando_codigo_ya_existe(auth_context_admin):
    # Arrange
    prod_existente = Productos(id_producto=1, codigo_producto="DUPLICADO", nombre="Test", precio_venta=Decimal("10.00"))
    prod_repo = FakeProductoRepo(productos=[prod_existente])
    service = ProductoService(producto_repo=prod_repo)

    # Act & Assert
    with pytest.raises(ReglaNegocioError) as exc_info:
        service.crear_producto(
            ctx=auth_context_admin,
            codigo_producto="DUPLICADO",
            nombre="Otro",
            precio_venta=Decimal("15.00"),
            id_categoria=1,
        )
    assert "ya existe (RI-02)" in str(exc_info.value)


@pytest.mark.unit
def test_debe_actualizar_precio_con_motivo_y_version_valida(auth_context_admin):
    # Arrange
    prod = Productos(id_producto=1, codigo_producto="PINT-01", nombre="Esmalte", precio_venta=Decimal("20000.00"), version=3)
    prod_repo = FakeProductoRepo(productos=[prod])
    hist_repo = FakeHistorialRepo()
    audit_port = FakeAuditPort()
    tx_manager = FakeTransactionManager()

    service = ProductoService(
        producto_repo=prod_repo,
        precio_repo=hist_repo,
        audit_port=audit_port,
        tx_manager=tx_manager,
    )

    # Act
    producto_actualizado = service.cambiar_precio(
        ctx=auth_context_admin,
        id_producto=1,
        nuevo_precio=Decimal("23000.00"),
        version=3,
        motivo="Ajuste por inflacion anual",
    )

    # Assert
    assert producto_actualizado.precio_venta == Decimal("23000.00")
    assert producto_actualizado.version == 4
    assert len(audit_port.registros) == 1
    assert audit_port.registros[0].accion == "CAMBIAR_PRECIO"


@pytest.mark.unit
def test_debe_rechazar_cambio_de_precio_si_motivo_esta_vacio(auth_context_admin):
    # Arrange
    service = ProductoService()

    # Act & Assert
    with pytest.raises(ReglaNegocioError) as exc_info:
        service.cambiar_precio(
            ctx=auth_context_admin,
            id_producto=1,
            nuevo_precio=Decimal("25000.00"),
            version=1,
            motivo="   ",
        )
    assert "motivo del cambio de precio es obligatorio" in str(exc_info.value)


@pytest.mark.unit
def test_debe_rechazar_cambio_de_precio_si_nuevo_precio_es_invalido(auth_context_admin):
    # Arrange
    service = ProductoService()

    # Act & Assert
    with pytest.raises(ReglaNegocioError) as exc_info:
        service.cambiar_precio(
            ctx=auth_context_admin,
            id_producto=1,
            nuevo_precio=Decimal("-500.00"),
            version=1,
            motivo="Error de tipeo",
        )
    assert "debe ser mayor a cero" in str(exc_info.value)


@pytest.mark.unit
def test_debe_lanzar_error_si_producto_a_cambiar_precio_no_existe(auth_context_admin):
    # Arrange
    prod_repo = FakeProductoRepo()
    tx_manager = FakeTransactionManager()
    service = ProductoService(producto_repo=prod_repo, tx_manager=tx_manager)

    # Act & Assert
    with pytest.raises(RecursoNoEncontradoError):
        service.cambiar_precio(
            ctx=auth_context_admin,
            id_producto=999,
            nuevo_precio=Decimal("10000.00"),
            version=1,
            motivo="No existe",
        )


@pytest.mark.unit
def test_debe_lanzar_409_conflicto_cuando_version_no_coincide(auth_context_admin):
    # Arrange
    prod = Productos(id_producto=5, codigo_producto="PINT-05", nombre="Laca", precio_venta=Decimal("18000.00"), version=2)
    prod_repo = FakeProductoRepo(productos=[prod])
    tx_manager = FakeTransactionManager()

    service = ProductoService(producto_repo=prod_repo, tx_manager=tx_manager)

    # Act & Assert
    with pytest.raises(ConflictoVersionError) as exc_info:
        service.cambiar_precio(
            ctx=auth_context_admin,
            id_producto=5,
            nuevo_precio=Decimal("19000.00"),
            version=1,  # Versión desactualizada
            motivo="Edicion concurrente",
        )
    assert "HTTP 409" in str(exc_info.value)


@pytest.mark.unit
def test_listar_productos_con_filtro():
    # Arrange
    prod1 = Productos(id_producto=1, codigo_producto="P1", nombre="Pintura Azul", precio_venta=Decimal("10000"), version=1)
    prod2 = Productos(id_producto=2, codigo_producto="P2", nombre="Brocha", precio_venta=Decimal("5000"), version=1)
    prod_repo = FakeProductoRepo(productos=[prod1, prod2])
    service = ProductoService(producto_repo=prod_repo)

    # Act
    resultado = service.listar_productos(termino="Azul", id_categoria=1)

    # Assert
    assert len(resultado) == 1
    assert resultado[0].nombre == "Pintura Azul"

