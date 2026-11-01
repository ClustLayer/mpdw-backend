# ==============================================================================
# Modelo de Eventos y Novedades - MPDW
# SAD Ref: M11, §8.1
# ==============================================================================
from django.db import models


class Eventos_novedades(models.Model):
    id_evento = models.BigAutoField(primary_key=True, db_column="id_evento")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.CASCADE, db_column="id_sede")
    titulo = models.CharField(max_length=150, db_column="titulo")
    descripcion = models.TextField(db_column="descripcion")
    fecha_evento = models.DateField(db_column="fecha_evento")
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_registro")

    class Meta:
        db_table = "Eventos_novedades"

