# ==============================================================================
# Modelo de Eventos y Novedades - MPDW
# SAD Ref: M11, §8.1
# ==============================================================================
from django.db import models

TIPO_PROMOCION = "promocion"
TIPO_CAPACITACION = "capacitacion"
TIPO_ENTREGA = "entrega"
TIPO_FESTIVO = "festivo"
TIPO_MANTENIMIENTO = "mantenimiento"
TIPO_SORTEO = "sorteo"

TIPOS_EVENTO_HU = (
    (TIPO_PROMOCION, "Promoción"),
    (TIPO_CAPACITACION, "Capacitación"),
    (TIPO_ENTREGA, "Entrega"),
    (TIPO_FESTIVO, "Festivo"),
    (TIPO_MANTENIMIENTO, "Mantenimiento"),
    (TIPO_SORTEO, "Sorteo"),
)

IMPACTO_ALTO = "Alto"
IMPACTO_MEDIO = "Medio"
IMPACTO_BAJO = "Bajo"

IMPACTOS = (
    (IMPACTO_ALTO, IMPACTO_ALTO),
    (IMPACTO_MEDIO, IMPACTO_MEDIO),
    (IMPACTO_BAJO, IMPACTO_BAJO),
)


class Eventos_novedades(models.Model):
    id_evento = models.BigAutoField(primary_key=True, db_column="id_evento")
    tipo = models.CharField(max_length=50, db_column="tipo")
    titulo = models.CharField(max_length=150, db_column="titulo")
    descripcion = models.TextField(db_column="descripcion")
    fecha_inicio = models.DateTimeField(db_column="fecha_inicio")
    fecha_fin = models.DateTimeField(null=True, blank=True, db_column="fecha_fin")
    impacto = models.CharField(max_length=10, choices=IMPACTOS, default=IMPACTO_MEDIO, db_column="impacto")
    areas_afectadas = models.TextField(blank=True, default="", db_column="areas_afectadas")
    id_sede = models.ForeignKey(
        "m02_sedes.Sedes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_sede",
    )
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_usuario",
    )
    estado = models.BooleanField(default=True, db_column="estado")
    visible_sitio = models.BooleanField(default=False, db_column="visible_sitio")
    imagen_url = models.CharField(max_length=500, blank=True, default="", db_column="imagen_url")
    importancia_clave = models.BooleanField(default=False, db_column="importancia_clave")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_registro")

    class Meta:
        db_table = "Eventos_novedades"
        indexes = [
            models.Index(fields=["fecha_inicio"], name="idx_evento_fecha_inicio"),
            models.Index(fields=["estado", "visible_sitio"], name="idx_evento_publico"),
        ]
