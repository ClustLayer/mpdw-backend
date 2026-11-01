# ==============================================================================
# Jerarquía de Excepciones de Dominio y Negocio - MPDW
# SAD Ref: §9.1, §10.5
# ==============================================================================
from typing import Any


class DominioError(Exception):
    """Excepción raíz de negocio para el sistema MPDW."""

    def __init__(self, mensaje: str, codigo: str = "ERROR_DOMINIO", detalles: list[Any] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.detalles = detalles or []


class ReglaNegocioError(DominioError):
    """Violación general de regla de negocio (HTTP 422)."""

    def __init__(self, mensaje: str, codigo: str = "REGLA_NEGOCIO_VIOLADA", detalles: list[Any] | None = None) -> None:
        super().__init__(mensaje, codigo=codigo, detalles=detalles)


class ConflictoVersionError(DominioError):
    """Colisión de concurrencia optimista sobre versión desactualizada (HTTP 409)."""

    def __init__(
        self,
        mensaje: str = "El registro fue modificado por otro usuario. Recargue para obtener la version mas reciente.",
        codigo: str = "CONFLICTO_CONCURRENCIA",
        detalles: list[Any] | None = None,
    ) -> None:
        super().__init__(mensaje, codigo=codigo, detalles=detalles)


class StockInsuficienteError(DominioError):
    """Intento de venta o salida con existencias insuficientes (HTTP 409)."""

    def __init__(
        self,
        mensaje: str = "Stock insuficiente para satisfacer la cantidad solicitada.",
        codigo: str = "STOCK_INSUFICIENTE",
        detalles: list[Any] | None = None,
    ) -> None:
        super().__init__(mensaje, codigo=codigo, detalles=detalles)


class RecursoNoEncontradoError(DominioError):
    """Entidad no encontrada en el repositorio (HTTP 404)."""

    def __init__(self, mensaje: str = "Recurso no encontrado.", codigo: str = "NO_ENCONTRADO") -> None:
        super().__init__(mensaje, codigo=codigo)


class SedeNoAutorizadaError(DominioError):
    """Acceso denegado a datos o recursos de una sede no asignada (HTTP 403)."""

    def __init__(self, mensaje: str = "No tiene autorizacion sobre la sede solicitada.", codigo: str = "SEDE_NO_AUTORIZADA") -> None:
        super().__init__(mensaje, codigo=codigo)


class AutenticacionError(DominioError):
    """Credenciales inválidas, token expirado o cuenta bloqueada (HTTP 401)."""

    def __init__(self, mensaje: str = "Credenciales invalidas.", codigo: str = "NO_AUTENTICADO") -> None:
        super().__init__(mensaje, codigo=codigo)


class PermisoDenegadoError(DominioError):
    """Acción denegada por la matriz de autorización (HTTP 403)."""

    def __init__(self, mensaje: str = "Permiso insuficiente para ejecutar esta accion.", codigo: str = "PERMISO_DENEGADO") -> None:
        super().__init__(mensaje, codigo=codigo)

