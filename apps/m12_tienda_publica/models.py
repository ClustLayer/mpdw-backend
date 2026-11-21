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


class Escaparate_seccion(models.Model):
    """Secciones visuales del inicio (carruseles del sitio público)."""

    id_escaparate = models.BigAutoField(primary_key=True, db_column="id_escaparate")
    clave = models.SlugField(max_length=80, unique=True, db_column="clave")
    frase = models.CharField(max_length=160, db_column="frase")
    titulo = models.CharField(max_length=160, db_column="titulo")
    enlace_catalogo = models.CharField(max_length=255, default="/catalogo", db_column="enlace_catalogo")
    color_acento = models.CharField(max_length=16, default="#E11D74", db_column="color_acento")
    orden = models.PositiveIntegerField(default=0, db_column="orden")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Escaparate_seccion"
        ordering = ["orden", "titulo"]


class Escaparate_producto(models.Model):
    id_escaparate_producto = models.BigAutoField(primary_key=True, db_column="id_escaparate_producto")
    id_escaparate = models.ForeignKey(
        Escaparate_seccion, on_delete=models.CASCADE, db_column="id_escaparate", related_name="productos"
    )
    id_producto = models.ForeignKey("m03_catalogo.Productos", on_delete=models.CASCADE, db_column="id_producto")
    orden = models.PositiveIntegerField(default=0, db_column="orden")

    class Meta:
        db_table = "Escaparate_producto"
        constraints = [
            models.UniqueConstraint(fields=["id_escaparate", "id_producto"], name="uq_escaparate_producto")
        ]
