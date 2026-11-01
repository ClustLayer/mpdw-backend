# ==============================================================================
# Repositorio y Adaptador de Lectura de Sedes - MPDW
# SAD Ref: M02, §6.4
# ==============================================================================
from apps.m02_sedes.models import Sedes
from contratos.puertos.sedes import SedeReadPort


class SedeRepository(SedeReadPort):
    """Acceso a datos de Sedes e implementación del puerto inter-módulo SedeReadPort."""

    def existe_sede_activa(self, id_sede: int) -> bool:
        return Sedes.objects.filter(pk=id_sede, estado=True).exists()

    def listar_ids_sedes_activas(self) -> list[int]:
        return list(Sedes.objects.filter(estado=True).values_list("id_sede", flat=True))

    def listar_activas(self):
        return Sedes.objects.filter(estado=True)

