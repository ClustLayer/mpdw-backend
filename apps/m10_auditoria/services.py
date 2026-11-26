# ==============================================================================
# Servicio y Adaptador de Auditoría - MPDW
# SAD Ref: M10, ADR-008, NF-07
# ==============================================================================
from __future__ import annotations

from typing import Any

from apps.m10_auditoria.repositories import AuditRepository
from apps.m13_plataforma.observability.constants import ACCIONES_SEGURIDAD_SQL
from apps.m13_plataforma.observability.general_log_writer import get_general_log_writer
from contratos.dtos import AuditoriaDTO
from contratos.puertos.auditoria import AuditPort


class AuditService(AuditPort):
    """Seguridad -> SQL; demás eventos -> log general Mongo (asíncrono)."""

    def __init__(self, repository: AuditRepository | None = None) -> None:
        self._repo = repository or AuditRepository()

    def registrar(self, dto: AuditoriaDTO) -> None:
        accion = str(dto.accion or "").upper()
        if accion in ACCIONES_SEGURIDAD_SQL:
            self._repo.insertar(dto)
            return
        self._mongo_desde_dto(dto)

    def _mongo_desde_dto(self, dto: AuditoriaDTO) -> None:
        doc: dict[str, Any] = {
            "tipo": "auditoria_negocio",
            "id_usuario": dto.id_usuario,
            "accion": dto.accion,
            "entidad": dto.entidad,
            "id_entidad": dto.id_entidad,
            "motivo": dto.motivo,
            "resultado": dto.resultado,
            "ip": dto.ip,
            "user_agent": dto.user_agent,
            "id_correlacion": dto.id_correlacion,
            "datos_antes": dto.datos_antes,
            "datos_despues": dto.datos_despues,
        }
        get_general_log_writer().enqueue(doc)
