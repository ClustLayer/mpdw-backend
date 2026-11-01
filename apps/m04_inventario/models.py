# ==============================================================================
# Modelos de Inventario y Kardex Append-Only - MPDW
# SAD Ref: M04, ADR-005, §8.1, RI-04, RI-05, RI-15, G-12
# ==============================================================================
from django.db import models


class Inventarios(models.Model):
    """Existencias físicas y reservas por producto y sede (SAD §8.1, RI-05)."""

    id_inventario = models.BigAutoField(primary_key=True, db_column="id_inventario")
    id_producto = models.ForeignKey("m03_catalogo.Productos", on_delete=models.CASCADE, db_column="id_producto")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.CASCADE, db_column="id_sede")
    cantidad_actual = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="cantidad_actual")
    cantidad_reservada = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="cantidad_reservada")

    class Meta:
        db_table = "Inventarios"
        constraints = [
            # RI-05: Una fila por producto y sede
            models.UniqueConstraint(fields=["id_producto", "id_sede"], name="uq_inventario_producto_sede"),
            # RI-04: Stock nunca negativo y reservado >= 0
            models.CheckConstraint(
                condition=models.Q(cantidad_actual__gte=0) & models.Q(cantidad_reservada__gte=0),
                name="chk_stock_no_negativo",
            ),
        ]

    def __str__(self) -> str:
        return f"Prod#{self.id_producto_id} @ Sede#{self.id_sede_id}: {self.cantidad_actual}"


class Movimientos_inventario(models.Model):
    """Kardex de inventario inmutable y append-only (SAD §8.1, RI-15)."""

    id_movimiento = models.BigAutoField(primary_key=True, db_column="id_movimiento")
    id_inventario = models.ForeignKey(Inventarios, on_delete=models.CASCADE, db_column="id_inventario", related_name="movimientos")
    tipo_movimiento = models.CharField(max_length=30, db_column="tipo_movimiento")
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, db_column="cantidad")
    cantidad_anterior = models.DecimalField(max_digits=14, decimal_places=2, db_column="cantidad_anterior")
    cantidad_nueva = models.DecimalField(max_digits=14, decimal_places=2, db_column="cantidad_nueva")
    motivo = models.TextField(db_column="motivo")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.DO_NOTHING,
        db_column="id_usuario",
        null=True,
        blank=True,
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Movimientos_inventario"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["id_inventario", "fecha_hora"], name="idx_kardex_inventario_fecha"),
        ]

    def __str__(self) -> str:
        return f"[{self.fecha_hora}] {self.tipo_movimiento} ({self.cantidad}) -> Nuevo: {self.cantidad_nueva}"

