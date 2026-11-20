# ==============================================================================
# Modelos del Catálogo de Productos - MPDW
# SAD Ref: M03, ADR-005, §8.1, G-08, RI-02, RI-26, IX-1
# ==============================================================================
from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Categorias_producto(models.Model):
    """Categorías de productos (SAD §8.1)."""

    id_categoria = models.BigAutoField(primary_key=True, db_column="id_categoria")
    nombre = models.CharField(max_length=255, unique=True, db_column="nombre")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Categorias_producto"

    def __str__(self) -> str:
        return self.nombre


class Marcas(models.Model):
    """Marcas de fabricantes (SAD §8.1)."""

    id_marca = models.BigAutoField(primary_key=True, db_column="id_marca")
    nombre = models.CharField(max_length=255, unique=True, db_column="nombre")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Marcas"

    def __str__(self) -> str:
        return self.nombre


class Tipos_producto(models.Model):
    """Tipos de productos (SAD §8.1)."""

    id_tipo_producto = models.BigAutoField(primary_key=True, db_column="id_tipo_producto")
    nombre = models.CharField(max_length=255, unique=True, db_column="nombre")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    afecta_venta_diaria = models.BooleanField(default=True, db_column="afecta_venta_diaria")
    es_base = models.BooleanField(default=False, db_column="es_base")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Tipos_producto"

    def __str__(self) -> str:
        return self.nombre


class Productos(models.Model):
    """Entidad principal de producto con control de concurrencia optimista (G-08)."""

    ORIGEN_COMPRADO = "comprado"
    ORIGEN_FABRICADO = "fabricado"
    ORIGEN_CHOICES = [(ORIGEN_COMPRADO, "Comprado"), (ORIGEN_FABRICADO, "Fabricado")]

    id_producto = models.BigAutoField(primary_key=True, db_column="id_producto")
    codigo_producto = models.CharField(max_length=50, unique=True, db_column="codigo_producto")  # RI-02
    codigo_barras = models.CharField(max_length=50, unique=True, null=True, blank=True, db_column="codigo_barras")  # RI-02
    nombre = models.CharField(max_length=255, db_column="nombre")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    unidad_medida = models.CharField(max_length=20, default="UND", db_column="unidad_medida")
    precio_compra = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="precio_compra")
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, db_column="precio_venta")
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="iva_porcentaje")
    stock_minimo = models.PositiveIntegerField(default=0, db_column="stock_minimo")
    imagen_url = models.CharField(max_length=500, blank=True, default="", db_column="imagen_url")
    id_categoria = models.ForeignKey(
        Categorias_producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_categoria",
    )
    id_marca = models.ForeignKey(Marcas, on_delete=models.SET_NULL, null=True, blank=True, db_column="id_marca")
    id_tipo_producto = models.ForeignKey(Tipos_producto, on_delete=models.SET_NULL, null=True, blank=True, db_column="id_tipo_producto")
    inventario_habilitado = models.BooleanField(default=True, db_column="inventario_habilitado")  # BR-07
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default=ORIGEN_COMPRADO,
        db_column="origen",
    )
    version = models.IntegerField(default=1, db_column="version")  # G-08: Concurrencia optimista
    estado = models.BooleanField(default=True, db_column="estado")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "Productos"
        indexes = [
            GinIndex(
                name="idx_productos_nombre_trgm",
                fields=["nombre"],
                opclasses=["gin_trgm_ops"],
            ),
            models.Index(fields=["estado", "nombre"], name="idx_productos_estado_nombre"),
            models.Index(fields=["id_categoria", "estado"], name="idx_productos_cat_estado"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_producto} - {self.nombre} (v{self.version})"


class Historial_precios(models.Model):
    """Vigencia histórica e inmutable de precios de venta (SAD §8.1, RI-26)."""

    id_historial = models.BigAutoField(primary_key=True, db_column="id_historial")
    id_producto = models.ForeignKey(Productos, on_delete=models.CASCADE, db_column="id_producto", related_name="historial_precios")
    precio_anterior = models.DecimalField(max_digits=14, decimal_places=2, db_column="precio_anterior")
    precio_nuevo = models.DecimalField(max_digits=14, decimal_places=2, db_column="precio_nuevo")
    precio_compra = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="precio_compra")
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, db_column="iva_porcentaje")
    fecha_inicio = models.DateTimeField(null=True, blank=True, db_column="fecha_inicio")
    motivo = models.TextField(db_column="motivo")  # TX-06: motivo obligatorio
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.DO_NOTHING,
        db_column="id_usuario",
        null=True,
        blank=True,
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True, db_column="fecha_cambio")
    fecha_fin = models.DateTimeField(null=True, blank=True, db_column="fecha_fin")

    class Meta:
        db_table = "Historial_precios"
        constraints = [
            # RI-26: Solo un precio vigente por producto (fecha_fin IS NULL)
            models.UniqueConstraint(
                fields=["id_producto"],
                condition=models.Q(fecha_fin__isnull=True),
                name="uq_historial_precio_vigente",
            ),
        ]
        indexes = [
            models.Index(fields=["id_producto", "-fecha_cambio"], name="idx_historial_prod_fecha"),
        ]

