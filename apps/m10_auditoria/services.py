# ==============================================================================
# Servicio y Adaptador de Auditoría - MPDW
# SAD Ref: M10, ADR-008, NF-07
# ==============================================================================
from apps.m10_auditoria.repositories import AuditRepository
from contratos.dtos import AuditoriaDTO
from contratos.puertos.auditoria import AuditPort


class AuditService(AuditPort):
    """Servicio de auditoría que implementa AuditPort para el resto de módulos."""

    def __init__(self, repository: AuditRepository | None = None) -> None:
        self._repo = repository or AuditRepository()

    def registrar(self, dto: AuditoriaDTO) -> None:
        self._repo.insertar(dto)

