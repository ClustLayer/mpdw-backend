"""Cálculos de totales, descuentos y margen para POS (Épica 8)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def _d(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def linea_bruto(cantidad: Decimal, precio: Decimal) -> Decimal:
    return (cantidad * precio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def descuento_linea(bruto: Decimal, pct: Decimal, valor: Decimal) -> Decimal:
    por_pct = (bruto * pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (por_pct + valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return min(total, bruto)


def calcular_lineas(lineas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ln in lineas:
        cantidad = _d(ln.get("cantidad"))
        precio = _d(ln.get("precio_unitario"))
        bruto = linea_bruto(cantidad, precio)
        desc = descuento_linea(bruto, _d(ln.get("descuento_porcentaje")), _d(ln.get("descuento_valor")))
        neto = (bruto - desc).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        iva_pct = _d(ln.get("iva_porcentaje"))
        iva = (neto * iva_pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        costo = _d(ln.get("costo_unitario"))
        out.append(
            {
                **ln,
                "bruto": bruto,
                "descuento_monto": desc,
                "neto": neto,
                "iva_monto": iva,
                "total_linea": (neto + iva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "margen": (neto - costo * cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            }
        )
    return out


def aplicar_descuento_general(lineas: list[dict[str, Any]], desc_general: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not desc_general:
        return lineas
    subtotal = sum(_d(x["neto"]) for x in lineas)
    if subtotal <= 0:
        return lineas
    tipo = (desc_general.get("tipo_descuento") or "PORCENTAJE").upper()
    monto = (
        (subtotal * _d(desc_general.get("porcentaje")) / Decimal("100"))
        if tipo.startswith("PORC")
        else _d(desc_general.get("valor"))
    )
    monto = min(monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), subtotal)
    for ln in lineas:
        parte = (monto * _d(ln["neto"]) / subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ln["neto"] = (_d(ln["neto"]) - parte).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        iva_pct = _d(ln.get("iva_porcentaje"))
        ln["iva_monto"] = (ln["neto"] * iva_pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ln["total_linea"] = (ln["neto"] + ln["iva_monto"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        costo = _d(ln.get("costo_unitario"))
        cantidad = _d(ln.get("cantidad"))
        ln["margen"] = (ln["neto"] - costo * cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return lineas


def totales_factura(lineas: list[dict[str, Any]]) -> dict[str, Decimal]:
    subtotal = sum(_d(x["neto"]) for x in lineas)
    descuento = sum(_d(x["descuento_monto"]) for x in lineas)
    impuesto = sum(_d(x["iva_monto"]) for x in lineas)
    total = sum(_d(x["total_linea"]) for x in lineas)
    margen = sum(_d(x["margen"]) for x in lineas)
    return {
        "subtotal": subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "descuento": descuento.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "impuesto": impuesto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "total": total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "margen": margen.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    }


def pct_descuento_acumulado(lineas: list[dict[str, Any]], desc_general: dict[str, Any] | None) -> Decimal:
    brutos = sum(_d(ln.get("bruto", 0)) for ln in lineas)
    if brutos <= 0:
        return Decimal("0")
    tot = totales_factura(aplicar_descuento_general(calcular_lineas(lineas), desc_general))
    ahorro = brutos - tot["subtotal"]
    return (ahorro / brutos * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)