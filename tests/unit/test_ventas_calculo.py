"""Cobertura unitaria de cálculos POS (Épica 8)."""

from decimal import Decimal

import pytest

from apps.m06_ventas.ventas_calculo import (
    _d,
    aplicar_descuento_general,
    calcular_lineas,
    descuento_linea,
    linea_bruto,
    totales_factura,
)


@pytest.mark.unit
def test_utilidades_decimal():
    assert _d(None) == Decimal("0")
    assert _d("no-numero") == Decimal("0")
    bruto = linea_bruto(Decimal(1), Decimal("50"))
    assert descuento_linea(bruto, Decimal("0"), bruto) == bruto


@pytest.mark.unit
def test_calcular_lineas_y_totales():
    raw = [
        {
            "cantidad": 2,
            "precio_unitario": Decimal("10000"),
            "descuento_porcentaje": Decimal("0"),
            "descuento_valor": Decimal("0"),
            "iva_porcentaje": Decimal("19"),
            "costo_unitario": Decimal("5000"),
        }
    ]
    lineas = calcular_lineas(raw)
    tot = totales_factura(lineas)
    assert tot["total"] > Decimal("0")
    assert lineas[0]["margen"] > Decimal("0")


@pytest.mark.unit
def test_descuento_general_porcentaje():
    raw = [
        {
            "cantidad": 1,
            "precio_unitario": Decimal("100"),
            "descuento_porcentaje": Decimal("0"),
            "descuento_valor": Decimal("0"),
            "iva_porcentaje": Decimal("0"),
            "costo_unitario": Decimal("40"),
        }
    ]
    lineas = calcular_lineas(raw)
    desc = {"tipo_descuento": "PORCENTAJE", "porcentaje": 10, "motivo": "Promo"}
    aplicadas = aplicar_descuento_general(lineas, desc)
    tot = totales_factura(aplicadas)
    assert tot["subtotal"] == Decimal("90.00")


@pytest.mark.unit
def test_totales_vacios_y_sin_descuento_general():
    assert totales_factura([])["total"] == Decimal("0.00")
    lineas = calcular_lineas(
        [
            {
                "cantidad": 1,
                "precio_unitario": Decimal("10"),
                "descuento_porcentaje": Decimal("0"),
                "descuento_valor": Decimal("0"),
                "iva_porcentaje": Decimal("0"),
                "costo_unitario": Decimal("0"),
            }
        ]
    )
    assert aplicar_descuento_general(lineas, None) == lineas
    assert aplicar_descuento_general(
        [],
        {"tipo_descuento": "PORCENTAJE", "porcentaje": 10, "motivo": "x"},
    ) == []


@pytest.mark.unit
def test_descuento_general_valor():
    raw = [
        {
            "cantidad": 1,
            "precio_unitario": Decimal("200"),
            "descuento_porcentaje": Decimal("0"),
            "descuento_valor": Decimal("0"),
            "iva_porcentaje": Decimal("0"),
            "costo_unitario": Decimal("50"),
        }
    ]
    desc = {"tipo_descuento": "VALOR", "valor": 25, "motivo": "Cortesía"}
    tot = totales_factura(aplicar_descuento_general(calcular_lineas(raw), desc))
    assert tot["subtotal"] == Decimal("175.00")
