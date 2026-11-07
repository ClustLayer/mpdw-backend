# ==============================================================================
# Repositorio de Auditoría - MPDW
# SAD Ref: M10, ADR-008
# ==============================================================================
from apps.m10_auditoria.models import Auditoria
from apps.m10_auditoria.sanitize import sanitize_auditoria_payload
from contratos.dtos import AuditoriaDTO


class AuditRepository:
    """Acceso a persistencia para registrar filas inmutables en Auditoria."""

    def insertar(self, dto: AuditoriaDTO) -> Auditoria:
        return Auditoria.objects.create(
            id_usuario_id=dto.id_usuario,
            accion=str(dto.accion)[:50],
            entidad=str(dto.entidad)[:100],
            id_entidad=dto.id_entidad,
            datos_antes=sanitize_auditoria_payload(dto.datos_antes),
            datos_despues=sanitize_auditoria_payload(dto.datos_despues),
            motivo=(dto.motivo or "").strip() or "—",
            resultado=dto.resultado,
            id_correlacion=dto.id_correlacion,
            ip=str(dto.ip or "127.0.0.1")[:45],
            user_agent=dto.user_agent,
        )

