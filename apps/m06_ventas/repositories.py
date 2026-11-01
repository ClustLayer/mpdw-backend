# ==============================================================================
# Repositorio y Adaptador de Ventas - MPDW
# SAD Ref: M06, ADR-001, §6.5
# ==============================================================================
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.m06_ventas.models import Facturas
from contratos.puertos.ventas import SalesReadPort


class SalesReadAdapter(SalesReadPort):
    """Implementa el puerto inter-módulo SalesReadPort para el módulo de caja M08."""

    def total_ventas_efectivo_jornada(self, id_sede: int, fecha: date) -> Decimal:
        resultado = (
            Facturas.objects.filter(
                id_sede_id=id_sede,
                fecha_hora__date=fecha,
                estado="EMITIDA",
            ).aggregate(total=Sum("total"))["total"]
        )
        return resultado or Decimal("0.00")

