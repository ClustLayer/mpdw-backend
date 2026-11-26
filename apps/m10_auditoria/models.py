# ==============================================================================
# Modelo de Auditoría Transaccional e Inmutable - MPDW (solo seguridad en SQL)
# SAD Ref: M10, ADR-008, NF-07, G-14, G-15, RI-16, IX-6
# ==============================================================================
from django.db import models


class Auditoria(models.Model):
    """Bitácora inmutable de eventos de seguridad (append-only)."""

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
    motivo = models.TextField(db_column="motivo")
    resultado = models.CharField(max_length=20, default="EXITO", db_column="resultado")
    ip = models.CharField(max_length=45, default="127.0.0.1", db_column="ip")
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Auditoria"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["id_usuario", "fecha_hora"], name="idx_auditoria_usuario"),
            models.Index(fields=["accion", "fecha_hora"], name="idx_auditoria_accion"),
        ]

    def __str__(self) -> str:
        return f"[{self.fecha_hora}] {self.accion} por {self.id_usuario_id}"
