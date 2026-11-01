# ==============================================================================
# Modelos del Catálogo de Productos - MPDW
# SAD Ref: M03, ADR-005, §8.1, G-08, RI-02, RI-26, IX-1
# ==============================================================================
from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Categorias_producto(models.Model):
    """Categorías de productos (SAD §8.1)."""

    id_categoria = models.BigAutoField(primary_key=True, db_column="id_categoria")
    nombre = models.CharField(max_length=100, unique=True, db_column="nombre")
    descripcion = models.CharField(max_length=200, blank=True, default="", db_column="descripcion")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Categorias_producto"

    def __str__(self) -> str:
        return self.nombre


class Marcas(models.Model):
    """Marcas de fabricantes (SAD §8.1)."""

    id_marca = models.BigAutoField(primary_key=True, db_column="id_marca")
    nombre = models.CharField(max_length=100, unique=True, db_column="nombre")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Marcas"

    def __str__(self) -> str:
        return self.nombre


class Tipos_producto(models.Model):
    """Tipos de productos (SAD §8.1)."""

    id_tipo_producto = models.BigAutoField(primary_key=True, db_column="id_tipo_producto")
    nombre = models.CharField(max_length=100, unique=True, db_column="nombre")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Tipos_producto"

    def __str__(self) -> str:
        return self.nombre


class Productos(models.Model):
    """Entidad principal de producto con control de concurrencia optimista (G-08)."""

    id_producto = models.BigAutoField(primary_key=True, db_column="id_producto")
    codigo_producto = models.CharField(max_length=50, unique=True, db_column="codigo_producto")  # RI-02
    codigo_barras = models.CharField(max_length=50, unique=True, null=True, blank=True, db_column="codigo_barras")  # RI-02
    nombre = models.CharField(max_length=200, db_column="nombre")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, db_column="precio_venta")
    id_categoria = models.ForeignKey(Categorias_producto, on_delete=models.PROTECT, db_column="id_categoria")
    id_marca = models.ForeignKey(Marcas, on_delete=models.SET_NULL, null=True, blank=True, db_column="id_marca")
    id_tipo_producto = models.ForeignKey(Tipos_producto, on_delete=models.SET_NULL, null=True, blank=True, db_column="id_tipo_producto")
    inventario_habilitado = models.BooleanField(default=True, db_column="inventario_habilitado")  # BR-07
    version = models.IntegerField(default=1, db_column="version")  # G-08: Concurrencia optimista
    estado = models.BooleanField(default=True, db_column="estado")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "Productos"
        indexes = [
            # IX-1: Búsqueda rápida por nombre con trigramas
            GinIndex(
                name="idx_productos_nombre_trgm",
                fields=["nombre"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_producto} - {self.nombre} (v{self.version})"


class Historial_precios(models.Model):
    """Vigencia histórica e inmutable de precios de venta (SAD §8.1, RI-26)."""

    id_historial = models.BigAutoField(primary_key=True, db_column="id_historial")
    id_producto = models.ForeignKey(Productos, on_delete=models.CASCADE, db_column="id_producto", related_name="historial_precios")
    precio_anterior = models.DecimalField(max_digits=14, decimal_places=2, db_column="precio_anterior")
    precio_nuevo = models.DecimalField(max_digits=14, decimal_places=2, db_column="precio_nuevo")
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

