# ==============================================================================
# Repositorios y Adaptador de Inventario - MPDW
# SAD Ref: M04, ADR-001, ADR-005, PR-3, TX-07
# ==============================================================================
from decimal import Decimal

from django.db.models import F

from apps.m04_inventario.models import Inventarios, Movimientos_inventario


class InventarioRepository:
    """Acceso a datos de Inventarios."""

    def obtener_o_crear(self, id_producto: int, id_sede: int, cantidad_inicial: Decimal = Decimal("0.00")) -> Inventarios:
        inv, _ = Inventarios.objects.get_or_create(
            id_producto_id=id_producto,
            id_sede_id=id_sede,
            defaults={"cantidad_actual": cantidad_inicial, "cantidad_reservada": Decimal("0.00")},
        )
        return inv

    def consultar_stock(self, id_producto: int, id_sede: int) -> Decimal:
        inv = Inventarios.objects.filter(id_producto_id=id_producto, id_sede_id=id_sede).first()
        return inv.cantidad_actual if inv else Decimal("0.00")

    def incrementar_stock(self, id_inventario: int, cantidad: Decimal) -> None:
        Inventarios.objects.filter(pk=id_inventario).update(
            cantidad_actual=F("cantidad_actual") + cantidad
        )


class MovimientoInventarioRepository:
    """Inserción append-only en el Kardex."""

    def registrar_movimiento(
        self,
        id_inventario: int,
        tipo_movimiento: str,
        cantidad: Decimal,
        cantidad_anterior: Decimal,
        cantidad_nueva: Decimal,
        motivo: str,
        id_usuario: int | None = None,
    ) -> Movimientos_inventario:
        return Movimientos_inventario.objects.create(
            id_inventario_id=id_inventario,
            tipo_movimiento=tipo_movimiento,
            cantidad=cantidad,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=cantidad_nueva,
            motivo=motivo,
            id_usuario_id=id_usuario,
        )

