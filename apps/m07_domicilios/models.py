# ==============================================================================
# Modelos de Domicilios y Mensajería - MPDW (Épica 9)
# SAD Ref: M07, §8.1, RI-19, RI-20, C-09, G-10
# ==============================================================================
from django.db import models


class Mensajeros(models.Model):
    id_mensajero = models.BigAutoField(primary_key=True, db_column="id_mensajero")
    nombre = models.CharField(max_length=255, db_column="nombre")
    apellido = models.CharField(max_length=255, db_column="apellido")
    documento = models.CharField(max_length=20, unique=True, db_column="documento")
    telefono = models.CharField(max_length=20, db_column="telefono")
    fecha_inicio = models.DateField(db_column="fecha_inicio")
    tarifa_promedio = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, db_column="tarifa_promedio"
    )
    observaciones = models.TextField(blank=True, default="", db_column="observaciones")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Mensajeros"


class Entregas(models.Model):
    ESTADOS_ACTIVOS = ("PENDIENTE", "ASIGNADO", "EN_CAMINO")

    id_entrega = models.BigAutoField(primary_key=True, db_column="id_entrega")
    id_factura = models.ForeignKey(
        "m06_ventas.Facturas",
        on_delete=models.CASCADE,
        db_column="id_factura",
        related_name="entregas",
    )
    id_mensajero = models.ForeignKey(
        Mensajeros,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_mensajero",
    )
    direccion = models.CharField(max_length=255, db_column="direccion")
    telefono_contacto = models.CharField(max_length=20, blank=True, default="", db_column="telefono_contacto")
    valor_cobrado_cliente = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor_cobrado_cliente")
    valor_pagado_mensajero = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor_pagado_mensajero")
    observaciones = models.CharField(max_length=500, blank=True, default="", db_column="observaciones")
    estado = models.CharField(max_length=30, default="PENDIENTE", db_column="estado")
    fecha_solicitud = models.DateTimeField(auto_now_add=True, db_column="fecha_solicitud")
    fecha_asignacion = models.DateTimeField(null=True, blank=True, db_column="fecha_asignacion")
    fecha_salida = models.DateTimeField(null=True, blank=True, db_column="fecha_salida")
    fecha_entrega = models.DateTimeField(null=True, blank=True, db_column="fecha_entrega")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Entregas"
        constraints = [
            models.UniqueConstraint(
                fields=["id_factura"],
                condition=models.Q(estado__in=["PENDIENTE", "ASIGNADO", "EN_CAMINO"]),
                name="uq_entrega_activa_por_factura",
            ),
        ]


class Historial_entregas(models.Model):
    id_historial = models.BigAutoField(primary_key=True, db_column="id_historial")
    id_entrega = models.ForeignKey(
        Entregas,
        on_delete=models.CASCADE,
        db_column="id_entrega",
        related_name="historial",
    )
    estado_anterior = models.CharField(max_length=30, null=True, blank=True, db_column="estado_anterior")
    estado_nuevo = models.CharField(max_length=30, db_column="estado_nuevo")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")
    observaciones = models.TextField(blank=True, default="", db_column="observaciones")

    class Meta:
        db_table = "Historial_entregas"
        ordering = ["-fecha_hora"]
