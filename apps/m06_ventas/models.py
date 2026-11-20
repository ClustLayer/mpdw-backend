# ==============================================================================
# Modelos de Ventas, Facturación y POS - MPDW (Épica 8)
# ==============================================================================
from django.db import models


class Tipos_venta(models.Model):
    id_tipo_venta = models.BigAutoField(primary_key=True, db_column="id_tipo_venta")
    nombre = models.CharField(max_length=50, unique=True, db_column="nombre")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Tipos_venta"


class Metodos_pago(models.Model):
    id_metodo_pago = models.BigAutoField(primary_key=True, db_column="id_metodo_pago")
    nombre = models.CharField(max_length=50, unique=True, db_column="nombre")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Metodos_pago"


ESTADOS_FACTURA = (
    "BORRADOR",
    "PENDIENTE_PAGO",
    "EMITIDA",
    "ANULADA",
    "DEVOLUCION_PARCIAL",
)


class Facturas(models.Model):
    """Factura / venta POS."""

    id_factura = models.BigAutoField(primary_key=True, db_column="id_factura")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.PROTECT, db_column="id_sede")
    serie = models.CharField(max_length=30, db_column="serie")
    numero_factura = models.CharField(max_length=50, db_column="numero_factura")
    id_cliente = models.ForeignKey(
        "m05_clientes.Clientes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_cliente",
    )
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios", on_delete=models.PROTECT, db_column="id_usuario"
    )
    id_tipo_venta = models.ForeignKey(
        Tipos_venta, on_delete=models.PROTECT, db_column="id_tipo_venta"
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, db_column="subtotal", default=0)
    descuento = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, db_column="descuento"
    )
    impuesto = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="impuesto")
    total = models.DecimalField(max_digits=14, decimal_places=2, db_column="total", default=0)
    estado = models.CharField(max_length=30, default="EMITIDA", db_column="estado")
    observaciones = models.TextField(blank=True, default="", db_column="observaciones")
    requiere_factura_electronica = models.BooleanField(
        default=False, db_column="requiere_factura_electronica"
    )
    requiere_domicilio = models.BooleanField(default=False, db_column="requiere_domicilio")
    requiere_revision_gerencial = models.BooleanField(
        default=False, db_column="requiere_revision_gerencial"
    )
    margen_negativo = models.BooleanField(default=False, db_column="margen_negativo")
    comprador_nombre = models.CharField(
        max_length=255, blank=True, default="", db_column="comprador_nombre"
    )
    comprador_documento = models.CharField(
        max_length=30, blank=True, default="", db_column="comprador_documento"
    )
    comprador_telefono = models.CharField(
        max_length=20, blank=True, default="", db_column="comprador_telefono"
    )
    comprador_correo = models.CharField(
        max_length=255, blank=True, default="", db_column="comprador_correo"
    )
    clave_idempotencia = models.CharField(
        max_length=128, unique=True, null=True, blank=True, db_column="clave_idempotencia"
    )
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Facturas"
        constraints = [
            models.UniqueConstraint(
                fields=["id_sede", "serie", "numero_factura"], name="uq_factura_consecutivo"
            ),
        ]
        indexes = [
            models.Index(fields=["estado", "fecha_hora"], name="idx_facturas_estado_fecha"),
            models.Index(fields=["id_usuario", "fecha_hora"], name="idx_facturas_usuario_fecha"),
            models.Index(
                fields=["margen_negativo", "fecha_hora"], name="idx_facturas_margen_fecha"
            ),
        ]


class Detalle_factura(models.Model):
    id_detalle = models.BigAutoField(primary_key=True, db_column="id_detalle")
    id_factura = models.ForeignKey(
        Facturas, on_delete=models.CASCADE, db_column="id_factura", related_name="detalles"
    )
    id_producto = models.ForeignKey(
        "m03_catalogo.Productos", on_delete=models.PROTECT, db_column="id_producto"
    )
    cantidad = models.DecimalField(max_digits=14, decimal_places=3, db_column="cantidad")
    precio_unitario = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, db_column="precio_unitario"
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, db_column="descuento_porcentaje"
    )
    descuento_valor = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, db_column="descuento_valor"
    )
    iva_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, db_column="iva_porcentaje"
    )
    iva_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, db_column="iva_monto"
    )
    costo_unitario = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, db_column="costo_unitario"
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, db_column="subtotal")
    cantidad_devuelta = models.DecimalField(
        max_digits=14, decimal_places=3, default=0, db_column="cantidad_devuelta"
    )

    class Meta:
        db_table = "Detalle_factura"


class Descuentos_factura(models.Model):
    id_descuento = models.BigAutoField(primary_key=True, db_column="id_descuento")
    id_factura = models.ForeignKey(
        Facturas, on_delete=models.CASCADE, db_column="id_factura", related_name="descuentos"
    )
    tipo_descuento = models.CharField(max_length=20, db_column="tipo_descuento")
    porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, db_column="porcentaje"
    )
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="valor")
    motivo = models.CharField(max_length=255, db_column="motivo")

    class Meta:
        db_table = "Descuentos_factura"


class Pagos(models.Model):
    id_pago = models.BigAutoField(primary_key=True, db_column="id_pago")
    id_factura = models.ForeignKey(
        Facturas, on_delete=models.CASCADE, db_column="id_factura", related_name="pagos"
    )
    id_metodo_pago = models.ForeignKey(
        Metodos_pago, on_delete=models.PROTECT, db_column="id_metodo_pago"
    )
    valor = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor")
    referencia = models.CharField(max_length=100, blank=True, default="", db_column="referencia")

    class Meta:
        db_table = "Pagos"


class Devoluciones(models.Model):
    id_devolucion = models.BigAutoField(primary_key=True, db_column="id_devolucion")
    id_factura = models.ForeignKey(
        Facturas, on_delete=models.CASCADE, db_column="id_factura", related_name="devoluciones"
    )
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios", on_delete=models.PROTECT, db_column="id_usuario"
    )
    motivo = models.CharField(max_length=255, db_column="motivo")
    total = models.DecimalField(max_digits=14, decimal_places=2, db_column="total")
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Devoluciones"


class Detalle_devolucion(models.Model):
    id_detalle_devolucion = models.BigAutoField(primary_key=True, db_column="id_detalle_devolucion")
    id_devolucion = models.ForeignKey(
        Devoluciones, on_delete=models.CASCADE, db_column="id_devolucion", related_name="lineas"
    )
    id_detalle_factura = models.ForeignKey(
        Detalle_factura, on_delete=models.PROTECT, db_column="id_detalle_factura"
    )
    cantidad = models.DecimalField(max_digits=14, decimal_places=3, db_column="cantidad")
    valor = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor")

    class Meta:
        db_table = "Detalle_devolucion"


class Facturas_electronicas(models.Model):
    id_factura_electronica = models.BigAutoField(
        primary_key=True, db_column="id_factura_electronica"
    )
    id_factura = models.OneToOneField(Facturas, on_delete=models.CASCADE, db_column="id_factura")
    estado = models.CharField(max_length=30, default="PENDIENTE", db_column="estado")
    tipo_nota = models.CharField(max_length=30, blank=True, default="", db_column="tipo_nota")
    referencia_externa = models.CharField(
        max_length=100, blank=True, default="", db_column="referencia_externa"
    )
    observacion = models.TextField(blank=True, default="", db_column="observacion")
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_registro")

    class Meta:
        db_table = "Facturas_electronicas"


class Consecutivos(models.Model):
    """Control de consecutivo por sede y serie (Épica 8 — cierra brecha B-5)."""

    id_consecutivo = models.BigAutoField(primary_key=True, db_column="id_consecutivo")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.CASCADE, db_column="id_sede")
    serie = models.CharField(max_length=30, db_column="serie")
    ultimo_numero = models.PositiveIntegerField(default=0, db_column="ultimo_numero")
    version = models.PositiveIntegerField(default=1, db_column="version")

    class Meta:
        db_table = "Consecutivos"
        constraints = [
            models.UniqueConstraint(fields=["id_sede", "serie"], name="uq_consecutivo_sede_serie"),
        ]
