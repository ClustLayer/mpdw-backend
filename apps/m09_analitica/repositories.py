from typing import Any

from django.db import connections


class AnaliticaRepository:
    """Consulta métricas agregadas desde el esquema analitica usando el alias 'bi'."""

    def obtener_resumen_ventas_diarias(self) -> list[dict[str, Any]]:
        with connections["bi"].cursor() as cursor:
            cursor.execute(
                "SELECT fecha, total_ventas, cantidad_facturas FROM analitica.ventas_diarias ORDER BY fecha DESC LIMIT 30"
            )
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

