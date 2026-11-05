# ==============================================================================
# Puerto de Correo Electrónico (SendGrid) - MPDW
# SAD Ref: E-02, I-07, §10.3
# ==============================================================================
from abc import ABC, abstractmethod


class EmailPort(ABC):
    """Puerto de borde para envío transaccional de correos (recuperación y 2FA)."""

    @abstractmethod
    def enviar_recuperacion_password(self, destinatario: str, enlace: str) -> bool:
        """Envía el enlace de un solo uso para restablecer contraseña."""
        pass

    @abstractmethod
    def enviar_codigo_2fa(self, destinatario: str, codigo: str) -> bool:
        """Envía el código de un solo uso del segundo factor. No registra el código."""
        pass

