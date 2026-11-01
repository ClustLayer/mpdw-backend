# ==============================================================================
# Servicio de Sedes - MPDW
# SAD Ref: M02, §6.4
# ==============================================================================
from apps.m02_sedes.repositories import SedeRepository


class SedeService:
    """Casos de uso para consulta y administración de sedes."""

    def __init__(self, repo: SedeRepository | None = None) -> None:
        self._repo = repo or SedeRepository()

    def listar_sedes(self):
        return self._repo.listar_activas()

