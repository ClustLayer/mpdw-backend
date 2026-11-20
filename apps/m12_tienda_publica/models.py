# ==============================================================================
# Modelos de Tienda Pública y Pedidos Web - MPDW (Épica 16, brecha B-2)
# ==============================================================================
from django.db import models

ESTADOS_PEDIDO = ("PENDIENTE", "CONFIRMADO", "CANCELADA")


class Pedidos_web(models.Model):
    """Pedido público vía WhatsApp; no descuenta inventario en este paso."""

    id_pedido_web = models.BigAutoField(primary_key=True, db_column="id_pedido_web")
    clave_idempotencia = models.CharField(max_length=128, unique=True, db_column="clave_idempotencia")
    nombre_contacto = models.CharField(max_length=255, db_column="nombre_contacto")
    telefono_contacto = models.CharField(max_length=20, db_column="telefono_contacto")
    direccion_entrega = models.CharField(max_length=500, blank=True, default="", db_column="direccion_entrega")
    observaciones = models.TextField(blank=True, default="", db_column="observaciones")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.PROTECT, db_column="id_sede")
    items_json = models.JSONField(db_column="items_json")
    total_estimado = models.DecimalField(max_digits=14, decimal_places=2, db_column="total_estimado")
    estado = models.CharField(max_length=20, default="PENDIENTE", db_column="estado")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "Pedidos_web"
