# ==============================================================================
# Catálogo Consolidado de Estados y Tipos - MPDW
# SAD Ref: §8.4, PR-5, C-02, C-03, C-05
# ==============================================================================
from enum import StrEnum


class EstadoUsuario(StrEnum):
    """Estados del ciclo de vida del usuario (SAD §8.4, C-11)."""
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    BLOQUEADO = "BLOQUEADO"


class RolBase(StrEnum):
    """Roles base protegidos contra eliminación (SAD §4.1, BR-10, Anexo A)."""
    ADMINISTRADOR = "Administrador"
    GERENTE = "Gerente"
    EMPLEADO = "Empleado"


class EstadoFactura(StrEnum):
    """Estados de la factura de venta (SAD §8.4, C-02)."""
    EMITIDA = "EMITIDA"
    ANULADA = "ANULADA"
    DEVOLUCION_PARCIAL = "DEVOLUCION_PARCIAL"


class EstadoFacturaElectronica(StrEnum):
    """Estados del registro local de FE sin transmisión DIAN (SAD §8.4, C-01, C-05, ADR-009)."""
    PENDIENTE = "PENDIENTE"
    GENERADA_EXTERNAMENTE = "GENERADA_EXTERNAMENTE"
    CANCELADA = "CANCELADA"


class EstadoReporteDiario(StrEnum):
    """Estados de la jornada de caja diaria (SAD §8.4, C-03)."""
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"
    AUDITADO = "AUDITADO"


class TipoMovimientoCaja(StrEnum):
    """Tipos de movimiento de caja segregados para analítica (SAD §5.1.1, BR-04, BR-11)."""
    GASTO = "GASTO"
    TRANSFERENCIA = "TRANSFERENCIA"
    AHORRO = "AHORRO"


class EstadoMovimientoCaja(StrEnum):
    """Estados de los movimientos de caja (SAD §8.4)."""
    ACTIVO = "ACTIVO"
    ANULADO = "ANULADO"


class TipoMovimientoInventario(StrEnum):
    """Sentido y causa del movimiento en kardex (SAD §8.4, RI-15, G-12)."""
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
    AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"
    TRASLADO_SALIDA = "TRASLADO_SALIDA"
    TRASLADO_ENTRADA = "TRASLADO_ENTRADA"
    ENTRADA_ANULACION = "ENTRADA_ANULACION"


class EstadoTraslado(StrEnum):
    """Estados de traslados entre sedes (SAD §8.4, C-10)."""
    PENDIENTE = "PENDIENTE"
    COMPLETADO = "COMPLETADO"
    CANCELADO = "CANCELADO"


class EstadoEntrega(StrEnum):
    """Estados de domicilios (SAD §8.4)."""
    PENDIENTE = "PENDIENTE"
    ASIGNADO = "ASIGNADO"
    EN_CAMINO = "EN_CAMINO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class VarianteCalculoEfectivo(StrEnum):
    """Variantes del cálculo de efectivo esperado en caja (SAD C-04, [Pendiente Q-02])."""
    VARIANTE_A = "VARIANTE_A"
    VARIANTE_B = "VARIANTE_B"


# ==============================================================================
# Matriz Oficial de Permisos por Rol Base según Anexo A del SAD
# 19 secciones × 3 roles = 57 celdas contractuales
#   'T' = Total / CRUD
#   'L' = Lectura / consulta
#   'O' = Operación transaccional
#   '—' = Sin acceso
# ==============================================================================
MATRIZ_ANEXO_A = [
    (1, "autenticacion_perfil", "Autenticacion y Perfil", "T", "T", "T"),
    (2, "usuarios", "Administracion de Usuarios", "—", "—", "T"),
    (3, "roles_permisos", "Roles y Permisos", "—", "—", "T"),
    (4, "sedes", "Gestion de Sedes", "—", "L", "T"),
    (5, "cuentas_bancarias", "Cuentas Bancarias", "—", "L", "T"),
    (6, "proveedores", "Directorio de Proveedores", "L", "T", "T"),
    (7, "catalogo_productos", "Catalogo de Productos", "L", "L", "T"),
    (8, "inventario_kardex", "Inventario y Kardex", "L", "T", "T"),
    (9, "clientes", "Directorio de Clientes", "T", "T", "T"),
    (10, "pos", "Punto de Venta (POS)", "O", "O", "T"),
    (11, "facturas", "Gestion y Anulacion de Facturas", "L", "T", "T"),
    (12, "domicilios", "Domicilios y Logistica", "O", "T", "T"),
    (13, "facturacion_electronica", "Registro de facturacion electronica (sin DIAN)", "—", "L", "T"),
    (14, "categorias_movimientos", "Categorias de Movimientos (CRUD 1)", "—", "L", "T"),
    (15, "gastos_frecuentes", "Gastos Frecuentes / Botones Rapidos (CRUD 2)", "—", "T", "T"),
    (16, "cierre_jornada", "Arqueo y Cierre de Jornada", "O", "T", "T"),
    (17, "eventos", "Eventos y Novedades", "—", "T", "T"),
    (18, "analitica", "Modulo de Ciencia de Datos / Analitica", "—", "L", "T"),
    (19, "auditoria", "Bitacora de Auditoria", "—", "L", "T"),
]


