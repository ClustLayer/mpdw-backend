# ==============================================================================
# Modelos de Domicilios y Mensajería - MPDW
# SAD Ref: M07, §8.1, RI-19, RI-20, C-09, G-10
# ==============================================================================
from django.db import models


class Mensajeros(models.Model):
    id_mensajero = models.BigAutoField(primary_key=True, db_column="id_mensajero")
    nombre = models.CharField(max_length=150, db_column="nombre")
    documento = models.CharField(max_length=20, unique=True, db_column="documento")
    telefono = models.CharField(max_length=20, db_column="telefono")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Mensajeros"


class Entregas(models.Model):
    id_entrega = models.BigAutoField(primary_key=True, db_column="id_entrega")
    id_factura = models.ForeignKey("m06_ventas.Facturas", on_delete=models.CASCADE, db_column="id_factura")
    id_mensajero = models.ForeignKey(Mensajeros, on_delete=models.SET_NULL, null=True, blank=True, db_column="id_mensajero")
    direccion_entrega = models.CharField(max_length=200, db_column="direccion_entrega")
    estado = models.CharField(max_length=20, default="PENDIENTE", db_column="estado")  # C-09, G-10
    fecha_solicitud = models.DateTimeField(auto_now_add=True, db_column="fecha_solicitud")

    class Meta:
        db_table = "Entregas"
        constraints = [
            # RI-19: A lo sumo una entrega no cancelada por factura
            models.UniqueConstraint(
                fields=["id_factura"],
                condition=~models.Q(estado="CANCELADO"),
                name="uq_entrega_activa_por_factura",
            ),
        ]

