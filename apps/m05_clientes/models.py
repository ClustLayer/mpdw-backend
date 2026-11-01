# ==============================================================================
# Modelos del Módulo M05: Clientes - MPDW
# SAD Ref: M05, §8.1. Tablas propias: Clientes, Tipos_cliente.
# ==============================================================================
from django.db import models


class Tipos_cliente(models.Model):
    id_tipo_cliente = models.BigAutoField(primary_key=True, db_column="id_tipo_cliente")
    nombre = models.CharField(max_length=50, unique=True, db_column="nombre")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Tipos_cliente"


class Clientes(models.Model):
    id_cliente = models.BigAutoField(primary_key=True, db_column="id_cliente")
    documento = models.CharField(max_length=20, unique=True, db_column="documento")
    nombre = models.CharField(max_length=150, db_column="nombre")
    telefono = models.CharField(max_length=20, blank=True, default="", db_column="telefono")
    email = models.EmailField(max_length=150, blank=True, default="", db_column="email")
    direccion = models.CharField(max_length=200, blank=True, default="", db_column="direccion")
    id_tipo_cliente = models.ForeignKey(Tipos_cliente, on_delete=models.PROTECT, db_column="id_tipo_cliente")
    consentimiento_datos = models.BooleanField(default=False, db_column="consentimiento_datos")  # RI-22
    fecha_consentimiento = models.DateTimeField(null=True, blank=True, db_column="fecha_consentimiento")  # RI-22
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Clientes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(consentimiento_datos=False) | models.Q(fecha_consentimiento__isnull=False),
                name="chk_consentimiento_fecha",
            ),
        ]

