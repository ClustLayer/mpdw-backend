# ==============================================================================
# Dominio de Cuadre de Caja - MPDW
# SAD Ref: M08, BR-01, C-04, [Pendiente Q-02]
# ==============================================================================
from decimal import Decimal
from enum import StrEnum


class VarianteCalculoEfectivo(StrEnum):
    """
    Variantes identificadas en el conflicto C-04 / Pregunta abierta Q-02:
    - VARIANTE_A: total_ventas comprende todos los medios de pago, y se descuentan las
      transferencias totales para aislar el efectivo neto en caja.
    - VARIANTE_B: ventas_efectivo contiene exclusivamente cobros en efectivo; por tanto,
      solo se descuentan transferencias manuales (no facturadas) para evitar doble descuento.
    """

    VARIANTE_A = "VARIANTE_A"
    VARIANTE_B = "VARIANTE_B"


def calcular_efectivo_esperado(
    base_inicial: Decimal,
    base_adicional: Decimal,
    ventas: Decimal,
    transferencias_a_descontar: Decimal,
    gastos: Decimal,
    ahorros: Decimal,
    entregas: Decimal = Decimal("0.00"),
    devoluciones: Decimal = Decimal("0.00"),
    variante: VarianteCalculoEfectivo = VarianteCalculoEfectivo.VARIANTE_B,
) -> Decimal:
    """
    Calcula el efectivo esperado al cierre de jornada.

    [Pendiente Q-02]: El Product Owner y la contabilidad deben ratificar cuál variante rige:
    - En Variante A: `ventas` es el gran total facturado y `transferencias_a_descontar` incluye
      todas las transferencias (facturadas y manuales).
    - En Variante B: `ventas` es solo efectivo cobrado y `transferencias_a_descontar` incluye
      únicamente transferencias manuales (para evitar doble resta).

    Fórmula:
        EfectivoEsperado = base_inicial + base_adicional + ventas - transferencias_a_descontar - gastos - ahorros - entregas - devoluciones
    """
    if variante not in (VarianteCalculoEfectivo.VARIANTE_A, VarianteCalculoEfectivo.VARIANTE_B):
        raise ValueError(f"Variante no soportada: {variante}")

    return (
        base_inicial
        + base_adicional
        + ventas
        - transferencias_a_descontar
        - gastos
        - ahorros
        - entregas
        - devoluciones
    )
