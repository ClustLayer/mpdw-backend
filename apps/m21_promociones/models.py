from django.db import models

TIPO_PROMOCION = "promocion"
TIPO_SORTEO = "sorteo"
TIPOS_PROMO = (
    (TIPO_PROMOCION, "Promoción"),
    (TIPO_SORTEO, "Sorteo"),
)

ESTADO_ACTIVA = "activa"
ESTADO_PAUSADA = "pausada"
ESTADOS = (
    (ESTADO_ACTIVA, "Activa"),
    (ESTADO_PAUSADA, "Pausada"),
)


class Promociones(models.Model):
    id_promocion = models.BigAutoField(primary_key=True, db_column="id_promocion")
    titulo = models.CharField(max_length=150, db_column="titulo")
    tipo = models.CharField(max_length=20, choices=TIPOS_PROMO, db_column="tipo")
    descripcion = models.TextField(db_column="descripcion")
    hashtags = models.CharField(max_length=500, blank=True, default="", db_column="hashtags")
    imagen = models.CharField(max_length=500, blank=True, default="", db_column="imagen")
    fecha_inicio = models.DateTimeField(db_column="fecha_inicio")
    fecha_fin = models.DateTimeField(null=True, blank=True, db_column="fecha_fin")
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_ACTIVA, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_registro")

    class Meta:
        db_table = "Promociones"
        indexes = [
            models.Index(fields=["estado", "fecha_inicio"], name="idx_promo_vigencia"),
        ]
