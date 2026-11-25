# ==============================================================================
# Repositorio de Auditoría - MPDW
# SAD Ref: M10, ADR-008
# ==============================================================================
from apps.m10_auditoria.models import Auditoria
from contratos.dtos import AuditoriaDTO


class AuditRepository:
    """Acceso a persistencia para registrar filas inmutables en Auditoria (seguridad)."""

    def insertar(self, dto: AuditoriaDTO) -> Auditoria:
        motivo = (dto.motivo or "").strip()
        if not motivo and (dto.datos_antes or dto.datos_despues):
            motivo = f"{dto.accion} · {dto.entidad}#{dto.id_entidad}"
        if not motivo:
            motivo = str(dto.accion)
        return Auditoria.objects.create(
            id_usuario_id=dto.id_usuario,
            accion=str(dto.accion)[:50],
            motivo=motivo[:4000],
            resultado=dto.resultado,
            ip=str(dto.ip or "127.0.0.1")[:45],
        )
