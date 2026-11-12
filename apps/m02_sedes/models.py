# ==============================================================================
# Modelo de Sedes - MPDW
# SAD Ref: M02, §8.1, G-20
# ==============================================================================
from django.conf import settings
from django.db import models


class Sedes(models.Model):
    """Sedes físicas y comerciales del negocio (SAD §8.1)."""

    id_sede = models.BigAutoField(primary_key=True, db_column="id_sede")
    nombre = models.CharField(max_length=255, db_column="nombre")
    direccion = models.CharField(max_length=255, db_column="direccion")
    telefono = models.CharField(max_length=20, blank=True, default="", db_column="telefono")
    whatsapp = models.CharField(max_length=20, blank=True, default="", db_column="whatsapp")
    ciudad = models.CharField(max_length=50, default="Cali", db_column="ciudad")
    maps_url = models.CharField(max_length=500, blank=True, default="", db_column="maps_url")
    map_query = models.CharField(max_length=255, blank=True, default="", db_column="map_query")
    orden = models.PositiveIntegerField(default=10, db_column="orden")
    estado = models.BooleanField(default=True, db_column="estado")
    es_principal = models.BooleanField(default=False, db_column="es_principal")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")
    id_usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_usuario_responsable",
        related_name="sedes_responsable",
    )

    class Meta:
        db_table = "Sedes"

    def __str__(self) -> str:
        return self.nombre


class Sede_horario(models.Model):
    """Horario por día de la semana (1=Lunes … 7=Domingo)."""

    id_horario = models.BigAutoField(primary_key=True, db_column="id_horario")
    id_sede = models.ForeignKey(
        Sedes, on_delete=models.CASCADE, db_column="id_sede", related_name="horarios"
    )
    dia_semana = models.PositiveSmallIntegerField(db_column="dia_semana")
    hora_apertura = models.TimeField(null=True, blank=True, db_column="hora_apertura")
    hora_cierre = models.TimeField(null=True, blank=True, db_column="hora_cierre")
    cerrado = models.BooleanField(default=False, db_column="cerrado")

    class Meta:
        db_table = "Sede_horario"
        constraints = [
            models.UniqueConstraint(fields=["id_sede", "dia_semana"], name="uq_sede_horario_dia")
        ]
