# ==============================================================================
# Modelos de Ventas, Facturación y Consecutivos - MPDW
# SAD Ref: M06, ADR-001, ADR-005, ADR-009, §8.1, G-03, G-04, G-05, RI-06
# ==============================================================================
from django.db import models


class Tipos_venta(models.Model):
    id_tipo_venta = models.BigAutoField(primary_key=True, db_column="id_tipo_venta")
    nombre = models.CharField(max_length=50, unique=True, db_column="nombre")

    class Meta:
        db_table = "Tipos_venta"


class Metodos_pago(models.Model):
    id_metodo_pago = models.BigAutoField(primary_key=True, db_column="id_metodo_pago")
    nombre = models.CharField(max_length=50, unique=True, db_column="nombre")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Metodos_pago"


class Consecutivos(models.Model):
    """Stub sin tabla física: G-03 no está en las 47 tablas aprobadas (Limitación registrada)."""
    id_consecutivo = models.BigAutoField(primary_key=True, db_column="id_consecutivo")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.CASCADE, db_column="id_sede")
    serie = models.CharField(max_length=10, db_column="serie")
    ultimo_numero = models.IntegerField(default=0, db_column="ultimo_numero")
    version = models.IntegerField(default=1, db_column="version")

    class Meta:
        managed = False
        db_table = "Consecutivos"


class Facturas(models.Model):
    """Factura / Venta POS (SAD §8.1, AD-01)."""
    id_factura = models.BigAutoField(primary_key=True, db_column="id_factura")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.PROTECT, db_column="id_sede")
    serie = models.CharField(max_length=10, db_column="serie")
    numero_factura = models.IntegerField(db_column="numero_factura")
    id_cliente = models.ForeignKey("m05_clientes.Clientes", on_delete=models.PROTECT, db_column="id_cliente")
    id_usuario = models.ForeignKey("m01_identidad.Usuarios", on_delete=models.PROTECT, db_column="id_usuario")
    id_tipo_venta = models.ForeignKey(Tipos_venta, on_delete=models.PROTECT, db_column="id_tipo_venta")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, db_column="subtotal")
    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="descuento")
    impuesto = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="impuesto")
    total = models.DecimalField(max_digits=14, decimal_places=2, db_column="total")
    estado = models.CharField(max_length=20, default="EMITIDA", db_column="estado")  # C-02
    clave_idempotencia = models.CharField(max_length=128, unique=True, null=True, blank=True, db_column="clave_idempotencia")  # SAD §9.3
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Facturas"
        constraints = [
            models.UniqueConstraint(fields=["id_sede", "serie", "numero_factura"], name="uq_factura_consecutivo"),
        ]


class Facturas_electronicas(models.Model):
    """Bandeja local de gestión manual externa sin integración DIAN (SAD C-01, C-05, ADR-009)."""
    id_factura_electronica = models.BigAutoField(primary_key=True, db_column="id_factura_electronica")
    id_factura = models.OneToOneField(Facturas, on_delete=models.CASCADE, db_column="id_factura")
    estado = models.CharField(max_length=30, default="PENDIENTE", db_column="estado")
    referencia_externa = models.CharField(max_length=100, blank=True, default="", db_column="referencia_externa")
    observacion = models.TextField(blank=True, default="", db_column="observacion")
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_registro")

    class Meta:
        db_table = "Facturas_electronicas"

