# ==============================================================================
# Modelo de Auditoría Transaccional e Inmutable - MPDW
# SAD Ref: M10, ADR-008, NF-07, G-14, G-15, RI-16, IX-6
# ==============================================================================
from django.db import models


class Auditoria(models.Model):
    """Bitácora inmutable de eventos sensibles del sistema (append-only)."""

    id_auditoria = models.BigAutoField(primary_key=True, db_column="id_auditoria")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.DO_NOTHING,
        db_column="id_usuario",
        null=True,
        blank=True,
        related_name="auditorias",
    )
    accion = models.CharField(max_length=50, db_column="accion")
    entidad = models.CharField(max_length=100, db_column="entidad")
    id_entidad = models.BigIntegerField(db_column="id_entidad")
    datos_antes = models.JSONField(null=True, blank=True, db_column="datos_antes")
    datos_despues = models.JSONField(null=True, blank=True, db_column="datos_despues")
    motivo = models.TextField(db_column="motivo")
    resultado = models.CharField(max_length=20, default="EXITO", db_column="resultado")
    id_correlacion = models.CharField(max_length=64, blank=True, default="", db_column="id_correlacion")
    ip = models.CharField(max_length=45, default="127.0.0.1", db_column="ip")
    user_agent = models.TextField(blank=True, default="", db_column="user_agent")
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Auditoria"
        ordering = ["-fecha_hora"]
        indexes = [
            # IX-6: Índices de auditoría para búsqueda por entidad, usuario o acción
            models.Index(fields=["entidad", "id_entidad", "fecha_hora"], name="idx_auditoria_entidad"),
            models.Index(fields=["id_usuario", "fecha_hora"], name="idx_auditoria_usuario"),
            models.Index(fields=["accion", "fecha_hora"], name="idx_auditoria_accion"),
        ]

    def __str__(self) -> str:
        return f"[{self.fecha_hora}] {self.accion} sobre {self.entidad}#{self.id_entidad} por {self.id_usuario_id}"

