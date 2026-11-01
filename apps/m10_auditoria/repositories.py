# ==============================================================================
# Repositorio de Auditoría - MPDW
# SAD Ref: M10, ADR-008
# ==============================================================================
from apps.m10_auditoria.models import Auditoria
from contratos.dtos import AuditoriaDTO


class AuditRepository:
    """Acceso a persistencia para registrar filas inmutables en Auditoria."""

    def insertar(self, dto: AuditoriaDTO) -> Auditoria:
        return Auditoria.objects.create(
            id_usuario_id=dto.id_usuario,
            accion=dto.accion,
            entidad=dto.entidad,
            id_entidad=dto.id_entidad,
            datos_antes=dto.datos_antes,
            datos_despues=dto.datos_despues,
            motivo=dto.motivo,
            resultado=dto.resultado,
            id_correlacion=dto.id_correlacion,
            ip=dto.ip,
            user_agent=dto.user_agent,
        )

