# ==============================================================================
# Modelos del Módulo M05: Clientes - MPDW
# SAD Ref: M05, §8.1. Tablas propias: Clientes, Tipos_cliente.
# ==============================================================================
from django.db import models


class Tipos_cliente(models.Model):
    id_tipo_cliente = models.BigAutoField(primary_key=True, db_column="id_tipo_cliente")
    nombre = models.CharField(max_length=50, unique=True, db_column="nombre")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    estado = models.BooleanField(default=True, db_column="estado")
    es_tipo_predeterminado = models.BooleanField(default=False, db_column="es_tipo_predeterminado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Tipos_cliente"


class Clientes(models.Model):
    id_cliente = models.BigAutoField(primary_key=True, db_column="id_cliente")
    nombre = models.CharField(max_length=255, db_column="nombre")
    apellido = models.CharField(max_length=255, blank=True, default="", db_column="apellido")
    numero_telefono = models.CharField(max_length=20, db_column="numero_telefono")
    tiene_whatsapp = models.BooleanField(default=False, db_column="tiene_whatsapp")
    direccion = models.CharField(max_length=255, blank=True, default="", db_column="direccion")
    ciudad = models.CharField(max_length=100, blank=True, default="", db_column="ciudad")
    documento = models.CharField(max_length=30, blank=True, default="", db_column="documento")
    correo = models.EmailField(max_length=255, blank=True, default="", db_column="correo")
    observaciones = models.TextField(blank=True, default="", db_column="observaciones")
    id_tipo_cliente = models.ForeignKey(Tipos_cliente, on_delete=models.PROTECT, db_column="id_tipo_cliente")
    consentimiento_datos = models.BooleanField(default=False, db_column="consentimiento_datos")
    fecha_consentimiento = models.DateTimeField(null=True, blank=True, db_column="fecha_consentimiento")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Clientes"
        indexes = [
            models.Index(fields=["numero_telefono"], name="idx_cliente_telefono"),
            models.Index(fields=["correo"], name="idx_cliente_correo"),
            models.Index(fields=["documento"], name="idx_cliente_documento"),
            models.Index(fields=["nombre"], name="idx_cliente_nombre"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(consentimiento_datos=False) | models.Q(fecha_consentimiento__isnull=False),
                name="chk_consentimiento_fecha",
            ),
            models.UniqueConstraint(
                fields=["documento"],
                condition=~models.Q(documento=""),
                name="uq_cliente_documento_no_vacio",
            ),
        ]
