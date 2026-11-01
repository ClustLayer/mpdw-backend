# ==============================================================================
# Repositorio y Adaptador de Caja - MPDW
# SAD Ref: M08, ADR-001, §6.5
# ==============================================================================
from apps.m08_caja.models import Reportes_diarios
from contratos.puertos.caja import CashPort


class CashAdapter(CashPort):
    """Implementa el puerto inter-módulo CashPort para el módulo de ventas M06."""

    def jornada_esta_abierta(self, id_sede: int) -> bool:
        return Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="ABIERTO").exists()

