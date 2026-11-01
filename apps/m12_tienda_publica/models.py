# ==============================================================================
# Modelos de Tienda Pública y Pedidos Web - MPDW
# SAD Ref: M12, G-01, AD-21, I-01
# ==============================================================================
from django.db import models


class Pedidos_web(models.Model):
    """Stub sin tabla física: G-01 no está en las 47 tablas aprobadas (Limitación registrada)."""
    id_pedido_web = models.BigAutoField(primary_key=True, db_column="id_pedido_web")
    clave_idempotencia = models.CharField(max_length=128, unique=True, db_column="clave_idempotencia")  # SAD §9.3
    nombre_contacto = models.CharField(max_length=150, db_column="nombre_contacto")
    telefono_contacto = models.CharField(max_length=20, db_column="telefono_contacto")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.PROTECT, db_column="id_sede")
    items_json = models.JSONField(db_column="items_json")
    total_estimado = models.DecimalField(max_digits=14, decimal_places=2, db_column="total_estimado")
    estado = models.CharField(max_length=20, default="PENDIENTE", db_column="estado")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        managed = False
        db_table = "Pedidos_web"

