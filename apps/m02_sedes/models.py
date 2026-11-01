# ==============================================================================
# Modelo de Sedes - MPDW
# SAD Ref: M02, §8.1, G-20
# ==============================================================================
from django.db import models


class Sedes(models.Model):
    """Sedes físicas y comerciales del negocio (SAD §8.1)."""

    id_sede = models.BigAutoField(primary_key=True, db_column="id_sede")
    nombre = models.CharField(max_length=100, db_column="nombre")
    direccion = models.CharField(max_length=200, db_column="direccion")
    telefono = models.CharField(max_length=20, blank=True, default="", db_column="telefono")
    ciudad = models.CharField(max_length=50, default="Bogota", db_column="ciudad")
    estado = models.BooleanField(default=True, db_column="estado")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "Sedes"

    def __str__(self) -> str:
        return self.nombre

