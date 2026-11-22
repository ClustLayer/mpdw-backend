# ==============================================================================
# Modelos de Caja, Jornada y Movimientos - MPDW
# SAD Ref: M08, ADR-001, ADR-005, §8.1, RI-09, RI-10, RI-12, BR-01, C-03, C-04
# ==============================================================================
from django.db import models

TIPOS_CUENTA = (
    "Nequi",
    "Bancolombia",
    "Davivienda",
    "NuBanq",
    "Banco Agrario",
    "Banco AVVILLAS",
)

ESTADOS_REPORTE = ("ABIERTO", "CERRADO", "AUDITADO")
TIPOS_CATEGORIA_MOV = ("Gasto", "Transferencia", "Ahorro")
ORIGEN_TRANSFERENCIA = ("VENTA", "MANUAL")


class Cuentas_bancarias(models.Model):
    """Cuenta bancaria; el campo `nombre` identifica al titular."""
    id_cuenta_bancaria = models.BigAutoField(primary_key=True, db_column="id_cuenta_bancaria")
    nombre = models.CharField(max_length=150, db_column="nombre", default="")
    banco = models.CharField(max_length=100, db_column="banco")
    tipo_cuenta = models.CharField(max_length=50, db_column="tipo_cuenta")
    numero = models.CharField(max_length=50, db_column="numero")  # G-23: cifrado/enmascarado
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

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
    base_adicional = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="base_adicional")
    venta_registrada = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="venta_registrada")
    total_ventas = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="total_ventas")
    total_transferencias = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="total_transferencias")
    total_gastos = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="total_gastos")
    total_ahorros = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="total_ahorros")
    total_entregas = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="total_entregas")
    saldo_caja_efectivo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="saldo_caja_efectivo")
    observaciones = models.TextField(blank=True, default="", db_column="observaciones")
    observaciones_cierre = models.TextField(blank=True, default="", db_column="observaciones_cierre")
    id_usuario_cierre = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="id_usuario_cierre",
        related_name="reportes_cerrados",
    )
    id_usuario_auditoria = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="id_usuario_auditoria",
        related_name="reportes_auditados",
    )
    fecha_auditoria = models.DateTimeField(null=True, blank=True, db_column="fecha_auditoria")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

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


class Categorias_movimiento(models.Model):
    id_categoria_movimiento = models.BigAutoField(primary_key=True, db_column="id_categoria_movimiento")
    nombre = models.CharField(max_length=100, db_column="nombre")
    tipo_movimiento = models.CharField(max_length=30, db_column="tipo_movimiento")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Categorias_movimiento"
        constraints = [
            models.UniqueConstraint(fields=["nombre", "tipo_movimiento"], name="uq_categoria_nombre_tipo"),
        ]


class Conceptos_movimiento(models.Model):
    id_concepto_movimiento = models.BigAutoField(primary_key=True, db_column="id_concepto_movimiento")
    id_categoria = models.ForeignKey(Categorias_movimiento, on_delete=models.PROTECT, db_column="id_categoria")
    nombre = models.CharField(max_length=255, db_column="nombre")
    valor_sugerido = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column="valor_sugerido")
    descripcion = models.TextField(blank=True, default="", db_column="descripcion")
    estado = models.BooleanField(default=True, db_column="estado")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")

    class Meta:
        db_table = "Conceptos_movimiento"


class Gastos_caja(models.Model):
    id_gasto = models.BigAutoField(primary_key=True, db_column="id_gasto")
    id_reporte_diario = models.ForeignKey(Reportes_diarios, on_delete=models.CASCADE, db_column="id_reporte_diario")
    id_categoria = models.ForeignKey(Categorias_movimiento, on_delete=models.PROTECT, db_column="id_categoria")
    id_concepto = models.ForeignKey(
        Conceptos_movimiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_concepto",
    )
    valor = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor")
    descripcion = models.TextField(db_column="descripcion")
    anulado = models.BooleanField(default=False, db_column="anulado")
    motivo_anulacion = models.CharField(max_length=255, blank=True, default="", db_column="motivo_anulacion")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Gastos"


class Ahorros(models.Model):
    id_ahorro = models.BigAutoField(primary_key=True, db_column="id_ahorro")
    id_reporte_diario = models.ForeignKey(Reportes_diarios, on_delete=models.CASCADE, db_column="id_reporte_diario")
    id_categoria = models.ForeignKey(Categorias_movimiento, on_delete=models.PROTECT, db_column="id_categoria")
    id_concepto = models.ForeignKey(
        Conceptos_movimiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_concepto",
    )
    valor = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor")
    descripcion = models.TextField(db_column="descripcion")
    anulado = models.BooleanField(default=False, db_column="anulado")
    motivo_anulacion = models.CharField(max_length=255, blank=True, default="", db_column="motivo_anulacion")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Ahorros"


class Transferencias_caja(models.Model):
    id_transferencia = models.BigAutoField(primary_key=True, db_column="id_transferencia")
    id_reporte_diario = models.ForeignKey(Reportes_diarios, on_delete=models.CASCADE, db_column="id_reporte_diario")
    id_categoria = models.ForeignKey(Categorias_movimiento, on_delete=models.PROTECT, db_column="id_categoria")
    id_cuenta_bancaria = models.ForeignKey(Cuentas_bancarias, on_delete=models.PROTECT, db_column="id_cuenta_bancaria")
    id_pago = models.ForeignKey(
        "m06_ventas.Pagos",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_pago",
    )
    valor = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor")
    referencia = models.CharField(max_length=100, db_column="referencia")
    observaciones = models.CharField(max_length=255, blank=True, default="", db_column="observaciones")
    origen = models.CharField(max_length=20, default="MANUAL", db_column="origen")
    editable = models.BooleanField(default=True, db_column="editable")
    anulado = models.BooleanField(default=False, db_column="anulado")
    motivo_anulacion = models.CharField(max_length=255, blank=True, default="", db_column="motivo_anulacion")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Transferencias"


class Adiciones_base(models.Model):
    id_adicion = models.BigAutoField(primary_key=True, db_column="id_adicion")
    id_reporte_diario = models.ForeignKey(Reportes_diarios, on_delete=models.CASCADE, db_column="id_reporte_diario")
    valor = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor")
    motivo = models.CharField(max_length=255, db_column="motivo")
    anulado = models.BooleanField(default=False, db_column="anulado")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Adiciones_base"


class Entregas_dinero(models.Model):
    id_entrega = models.BigAutoField(primary_key=True, db_column="id_entrega")
    id_reporte_diario = models.ForeignKey(Reportes_diarios, on_delete=models.CASCADE, db_column="id_reporte_diario")
    valor = models.DecimalField(max_digits=14, decimal_places=2, db_column="valor")
    descripcion = models.CharField(max_length=255, db_column="descripcion")
    anulado = models.BooleanField(default=False, db_column="anulado")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Entregas_dinero"


class Adjuntos_movimiento(models.Model):
    id_adjunto = models.BigAutoField(primary_key=True, db_column="id_adjunto")
    id_gasto = models.ForeignKey(Gastos_caja, on_delete=models.CASCADE, null=True, blank=True, db_column="id_gasto")
    id_transferencia = models.ForeignKey(
        Transferencias_caja,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column="id_transferencia",
    )
    nombre_original = models.CharField(max_length=255, db_column="nombre_original")
    ruta_almacenamiento = models.CharField(max_length=255, db_column="ruta_almacenamiento")
    tipo_mime = models.CharField(max_length=100, db_column="tipo_mime")
    tamano_bytes = models.BigIntegerField(db_column="tamano_bytes")
    hash_integridad = models.CharField(max_length=128, db_column="hash_integridad")
    id_usuario = models.ForeignKey(
        "m01_identidad.Usuarios",
        on_delete=models.PROTECT,
        db_column="id_usuario",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")

    class Meta:
        db_table = "Adjuntos_movimiento"

