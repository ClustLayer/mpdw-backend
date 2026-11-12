# ==============================================================================
# Modelos del Módulo M14: Proveedores - MPDW
# ==============================================================================
from django.db import models

TIPO_DOC_NIT = "NIT"
TIPO_DOC_CC = "CC"
TIPO_DOC_PASAPORTE = "Pasaporte"

TIPOS_DOCUMENTO = (
    (TIPO_DOC_NIT, TIPO_DOC_NIT),
    (TIPO_DOC_CC, TIPO_DOC_CC),
    (TIPO_DOC_PASAPORTE, TIPO_DOC_PASAPORTE),
)


class Proveedores(models.Model):
    id_proveedor = models.BigAutoField(primary_key=True, db_column="id_proveedor")
    nombre = models.CharField(max_length=255, db_column="nombre")
    tipo_documento = models.CharField(max_length=20, choices=TIPOS_DOCUMENTO, db_column="tipo_documento")
    numero_documento = models.CharField(max_length=30, blank=True, default="", db_column="numero_documento")
    contacto_nombre = models.CharField(max_length=255, blank=True, default="", db_column="contacto_nombre")
    contacto_cargo = models.CharField(max_length=120, blank=True, default="", db_column="contacto_cargo")
    telefono = models.CharField(max_length=20, blank=True, default="", db_column="telefono")
    correo = models.EmailField(max_length=255, blank=True, default="", db_column="correo")
    direccion = models.CharField(max_length=255, blank=True, default="", db_column="direccion")
    ciudad = models.CharField(max_length=100, blank=True, default="", db_column="ciudad")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    productos_suministra = models.TextField(blank=True, default="", db_column="productos_suministra")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_registro")

    class Meta:
        db_table = "Proveedores"
        indexes = [
            models.Index(fields=["nombre"], name="idx_proveedor_nombre"),
            models.Index(fields=["numero_documento"], name="idx_proveedor_documento"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["numero_documento"],
                condition=~models.Q(numero_documento=""),
                name="uq_proveedor_documento_no_vacio",
            ),
        ]
