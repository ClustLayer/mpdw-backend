# ==============================================================================
# Servicio de Dominio del Catálogo de Productos - MPDW
# SAD Ref: M03, ADR-005, ADR-008, TX-06, TX-07, TX-11, RI-02, RI-26
# ==============================================================================
from decimal import Decimal
from typing import Any

from apps.m03_catalogo.models import Productos
from apps.m03_catalogo.repositories import HistorialPreciosRepository, ProductoRepository
from contratos.dtos import AuditoriaDTO, AuthContext, StockInicialDTO
from contratos.excepciones import (
    ConflictoVersionError,
    RecursoNoEncontradoError,
    ReglaNegocioError,
)
from contratos.puertos.auditoria import AuditPort
from contratos.puertos.inventario import InventoryPort
from contratos.puertos.transaccion import GestorTransaccionPort


class ProductoService:
    """Casos de uso para creación de productos y actualización optimista de precios."""

    def __init__(
        self,
        producto_repo: ProductoRepository | None = None,
        precio_repo: HistorialPreciosRepository | None = None,
        inventory_port: InventoryPort | None = None,
        audit_port: AuditPort | None = None,
        tx_manager: GestorTransaccionPort | None = None,
    ) -> None:
        self._prod_repo = producto_repo or ProductoRepository()
        self._precio_repo = precio_repo or HistorialPreciosRepository()
        if inventory_port is None:
            from apps.m04_inventario.services import InventarioService

            self._inventory: InventoryPort | None = InventarioService()
        else:
            self._inventory = inventory_port
        self._audit = audit_port
        self._tx = tx_manager

    def listar_productos(self, termino: str | None = None, id_categoria: int | None = None) -> Any:
        """Búsqueda paginada y filtrada en el catálogo de productos."""
        return self._prod_repo.listar_con_filtro(termino=termino, id_categoria=id_categoria)

    def crear_producto(
        self,
        ctx: AuthContext,
        codigo_producto: str,
        nombre: str,
        precio_venta: Decimal,
        id_categoria: int,
        codigo_barras: str | None = None,
        descripcion: str = "",
        id_marca: int | None = None,
        id_tipo_producto: int | None = None,
        inventario_habilitado: bool = True,
        stocks_iniciales: list[StockInicialDTO] | None = None,
    ) -> Productos:
        """Alta atómica de producto con inventario inicial y auditoría en una transacción (TX-07)."""
        if precio_venta <= Decimal("0.00"):
            raise ReglaNegocioError("El precio de venta debe ser superior a cero.")

        if self._prod_repo.buscar_por_codigo(codigo_producto):
            raise ReglaNegocioError(f"El codigo de producto '{codigo_producto}' ya existe (RI-02).")

        def _ejecutar_creacion() -> Productos:
            producto = self._prod_repo.crear_producto(
                codigo_producto=codigo_producto,
                codigo_barras=codigo_barras,
                nombre=nombre,
                descripcion=descripcion,
                precio_venta=precio_venta,
                id_categoria_id=id_categoria,
                id_marca_id=id_marca,
                id_tipo_producto_id=id_tipo_producto,
                inventario_habilitado=inventario_habilitado,
            )

            # 1. Registrar vigencia inicial de precio (RI-26)
            self._precio_repo.registrar_nuevo_precio(
                id_producto=producto.id_producto,
                precio_anterior=Decimal("0.00"),
                precio_nuevo=precio_venta,
                motivo="Precio inicial de apertura de catalogo",
                id_usuario=ctx.id_usuario,
            )

            # 2. Inicializar existencias por sede a través del puerto inter-módulo (TX-07)
            if stocks_iniciales and self._inventory:
                self._inventory.inicializar_stock_producto(
                    id_producto=producto.id_producto,
                    stocks=stocks_iniciales,
                    motivo="Inventario inicial por alta de producto",
                )

            # 3. Auditar en la misma transacción (ADR-008)
            if self._audit:
                self._audit.registrar(
                    AuditoriaDTO(
                        id_usuario=ctx.id_usuario,
                        accion="CREAR_PRODUCTO",
                        entidad="Productos",
                        id_entidad=producto.id_producto,
                        datos_antes=None,
                        datos_despues={
                            "codigo_producto": producto.codigo_producto,
                            "nombre": producto.nombre,
                            "precio_venta": str(producto.precio_venta),
                            "version": producto.version,
                        },
                        motivo="Alta de producto con inventario inicial",
                        id_correlacion=ctx.id_correlacion,
                        ip=ctx.ip,
                        user_agent=ctx.user_agent,
                    )
                )

            return producto

        if self._tx:
            with self._tx.atomic():
                return _ejecutar_creacion()
        return _ejecutar_creacion()

    def cambiar_precio(
        self,
        ctx: AuthContext,
        id_producto: int,
        nuevo_precio: Decimal,
        version: int,
        motivo: str,
    ) -> Productos:
        """
        Cambio de precio con motivo obligatorio y control de concurrencia optimista (TX-06, TX-11).
        Lanza ConflictoVersionError (HTTP 409) si la versión difiere.
        """
        if not motivo or not motivo.strip():
            raise ReglaNegocioError("El motivo del cambio de precio es obligatorio (TX-06).")

        if nuevo_precio <= Decimal("0.00"):
            raise ReglaNegocioError("El nuevo precio debe ser mayor a cero.")

        def _ejecutar_cambio() -> Productos:
            producto = self._prod_repo.buscar_por_id(id_producto)
            if not producto:
                raise RecursoNoEncontradoError(f"Producto con id {id_producto} no encontrado.")

            precio_anterior = producto.precio_venta

            # Ejecutar UPDATE condicional atómico
            filas = self._prod_repo.actualizar_precio_concurrente(
                id_producto=id_producto,
                nuevo_precio=nuevo_precio,
                version_esperada=version,
            )

            if filas == 0:
                # 0 filas actualizadas significa que otro usuario ya modificó la versión
                raise ConflictoVersionError(
                    f"Conflicto de edicion (HTTP 409): El producto #{id_producto} tiene una version mas reciente que la version enviada (v{version})."
                )

            # Cerrar vigencia anterior y registrar la nueva
            self._precio_repo.cerrar_precio_vigente(id_producto)
            self._precio_repo.registrar_nuevo_precio(
                id_producto=id_producto,
                precio_anterior=precio_anterior,
                precio_nuevo=nuevo_precio,
                motivo=motivo.strip(),
                id_usuario=ctx.id_usuario,
            )

            # Auditar mutación de precio en la misma transacción
            if self._audit:
                self._audit.registrar(
                    AuditoriaDTO(
                        id_usuario=ctx.id_usuario,
                        accion="CAMBIAR_PRECIO",
                        entidad="Productos",
                        id_entidad=id_producto,
                        datos_antes={"precio_venta": str(precio_anterior), "version": version},
                        datos_despues={"precio_venta": str(nuevo_precio), "version": version + 1},
                        motivo=motivo.strip(),
                        id_correlacion=ctx.id_correlacion,
                        ip=ctx.ip,
                        user_agent=ctx.user_agent,
                    )
                )

            producto.precio_venta = nuevo_precio
            producto.version = version + 1
            return producto

        if self._tx:
            with self._tx.atomic():
                return _ejecutar_cambio()
        return _ejecutar_cambio()

