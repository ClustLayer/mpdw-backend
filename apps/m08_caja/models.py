# ==============================================================================
# Modelos de Caja, Jornada y Movimientos - MPDW
# SAD Ref: M08, ADR-001, ADR-005, §8.1, RI-09, RI-10, RI-12, BR-01, C-03, C-04
# ==============================================================================
from django.db import models


class Cuentas_bancarias(models.Model):
    id_cuenta_bancaria = models.BigAutoField(primary_key=True, db_column="id_cuenta_bancaria")
    banco = models.CharField(max_length=100, db_column="banco")
    tipo_cuenta = models.CharField(max_length=50, db_column="tipo_cuenta")
    numero = models.CharField(max_length=50, db_column="numero")  # G-23: cifrado/enmascarado
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Cuentas_bancarias"


class Reportes_diarios(models.Model):
    """Jornada de caja por sede y fecha (SAD §8.1, RI-09, RI-10)."""
    id_reporte_diario = models.BigAutoField(primary_key=True, db_column="id_reporte_diario")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.CASCADE, db_column="id_sede")
    fecha = models.DateField(db_column="fecha")
    base_inicial = models.DecimalField(max_digits=14, decimal_places=2, db_column="base_inicial")  # RI-12
    base_siguiente = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="base_siguiente")
    efectivo_esperado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="efectivo_esperado")
    efectivo_declarado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="efectivo_declarado")
    diferencia = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="diferencia")
    estado = models.CharField(max_length=20, default="ABIERTO", db_column="estado")  # C-03
    id_usuario_apertura = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario_apertura",
        related_name="reportes_abiertos",
    )
    fecha_apertura = models.DateTimeField(auto_now_add=True, db_column="fecha_apertura")
    fecha_cierre = models.DateTimeField(null=True, blank=True, db_column="fecha_cierre")

    class Meta:
        db_table = "Reportes_diarios"
        constraints = [
            # RI-09: Un reporte por sede y fecha
            models.UniqueConstraint(fields=["id_sede", "fecha"], name="uq_reporte_sede_fecha"),
            # RI-10: A lo sumo un reporte ABIERTO por sede
            models.UniqueConstraint(
                fields=["id_sede"],
                condition=models.Q(estado="ABIERTO"),
                name="uq_reporte_abierto_por_sede",
            ),
        ]

