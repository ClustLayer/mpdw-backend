# ==============================================================================
# Pruebas Unitarias de Reglas Monetarias y Cuadre de Caja - MPDW
# SAD Ref: BR-01, C-04, [Pendiente Q-02], K-07, Checklist C16
# ==============================================================================
from decimal import Decimal

import pytest

from apps.m08_caja.dominio import (
    VarianteCalculoEfectivo,
    calcular_efectivo_esperado,
)


def calcular_totales_lineas(
    cantidades_y_precios: list[tuple[Decimal, Decimal]],
    porcentaje_iva: Decimal = Decimal("0.19"),
    descuento_general: Decimal = Decimal("0.00"),
) -> tuple[Decimal, Decimal, Decimal]:
    """Función pura para cómputo de subtotal, IVA y total de factura."""
    subtotal = sum((cant * precio for cant, precio in cantidades_y_precios), Decimal("0.00"))
    subtotal_con_descuento = max(subtotal - descuento_general, Decimal("0.00"))
    iva = (subtotal_con_descuento * porcentaje_iva).quantize(Decimal("0.01"))
    total = subtotal_con_descuento + iva
    return subtotal, iva, total


@pytest.mark.unit
def test_totales_deben_calcularse_exclusivamente_con_decimal():
    cantidades_precios = [
        (Decimal("2.00"), Decimal("15000.50")),
        (Decimal("1.00"), Decimal("32000.00")),
    ]
    subtotal, iva, total = calcular_totales_lineas(cantidades_precios, porcentaje_iva=Decimal("0.19"))

    assert subtotal == Decimal("62001.00")
    assert iva == Decimal("11780.19")
    assert total == Decimal("73781.19")
    assert isinstance(total, Decimal)


@pytest.mark.unit
@pytest.mark.parametrize(
    "variante,base_inicial,base_adic,ventas,transferencias,gastos,ahorros,entregas,devoluciones,esperado",
    [
        # Variante A (C-04 / Q-02): Ventas totales (efectivo + transferencia), transferencias totales descontadas
        (
            VarianteCalculoEfectivo.VARIANTE_A,
            Decimal("200000.00"),
            Decimal("50000.00"),
            Decimal("2000000.00"),  # total ventas
            Decimal("500000.00"),   # transferencias totales facturadas y manuales
            Decimal("80000.00"),
            Decimal("200000.00"),
            Decimal("100000.00"),
            Decimal("20000.00"),
            Decimal("1350000.00"),  # 200k + 50k + 2000k - 500k - 80k - 200k - 100k - 20k
        ),
        # Variante B (C-04 / Q-02): Ventas segregadas en efectivo, transferencias solo manuales
        (
            VarianteCalculoEfectivo.VARIANTE_B,
            Decimal("200000.00"),
            Decimal("50000.00"),
            Decimal("1500000.00"),  # solo ventas en efectivo
            Decimal("100000.00"),   # solo transferencias manuales
            Decimal("80000.00"),
            Decimal("200000.00"),
            Decimal("50000.00"),
            Decimal("0.00"),
            Decimal("1320000.00"),  # 200k + 50k + 1500k - 100k - 80k - 200k - 50k
        ),
    ],
)
def test_cuadre_de_caja_parametrizado_ambas_variantes(
    variante,
    base_inicial,
    base_adic,
    ventas,
    transferencias,
    gastos,
    ahorros,
    entregas,
    devoluciones,
    esperado,
):
    resultado = calcular_efectivo_esperado(
        base_inicial=base_inicial,
        base_adicional=base_adic,
        ventas=ventas,
        transferencias_a_descontar=transferencias,
        gastos=gastos,
        ahorros=ahorros,
        entregas=entregas,
        devoluciones=devoluciones,
        variante=variante,
    )
    assert resultado == esperado
    assert isinstance(resultado, Decimal)


@pytest.mark.unit
def test_cuadre_de_caja_variante_invalida_lanza_error():
    with pytest.raises(ValueError, match="Variante no soportada"):
        calcular_efectivo_esperado(
            base_inicial=Decimal("100.00"),
            base_adicional=Decimal("0.00"),
            ventas=Decimal("100.00"),
            transferencias_a_descontar=Decimal("0.00"),
            gastos=Decimal("0.00"),
            ahorros=Decimal("0.00"),
            variante="VARIANTE_INVALIDA",  # type: ignore[arg-type]
        )
