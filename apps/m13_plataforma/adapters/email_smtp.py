# ==============================================================================
# Adaptador SMTP (Brevo u otro relay). No registra el cuerpo del mensaje.
# ==============================================================================
import logging
import smtplib
import ssl
from email.message import EmailMessage

from django.conf import settings

from apps.m13_plataforma.adapters.plantillas_correo import (
    html_codigo_2fa,
    html_contrasena_inicial,
    html_recuperacion,
)
from contratos.puertos.correo import EmailPort

logger = logging.getLogger(__name__)


class SmtpEmailAdapter(EmailPort):
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        remitente: str | None = None,
        nombre: str | None = None,
        use_tls: bool | None = None,
    ) -> None:
        self._host = host if host is not None else settings.SMTP_HOST
        self._port = port if port is not None else int(settings.SMTP_PORT)
        self._user = user if user is not None else settings.SMTP_USER
        self._password = password if password is not None else settings.SMTP_PASS
        self._remitente = remitente if remitente is not None else settings.SMTP_FROM_EMAIL
        self._nombre = nombre if nombre is not None else settings.SMTP_FROM_NAME
        self._use_tls = settings.SMTP_USE_TLS if use_tls is None else use_tls

    def enviar_recuperacion_password(self, destinatario: str, enlace: str) -> bool:
        return self._enviar(destinatario, "Restablecer contraseña - Mundo Pinturas Diana", html_recuperacion(enlace))

    def enviar_codigo_2fa(self, destinatario: str, codigo: str) -> bool:
        return self._enviar(destinatario, "Código de verificación - Mundo Pinturas Diana", html_codigo_2fa(codigo))

    def enviar_contrasena_inicial(self, destinatario: str, nombre: str, contrasena_plana: str) -> bool:
        return self._enviar(
            destinatario,
            "Acceso al sistema - Mundo Pinturas Diana",
            html_contrasena_inicial(nombre, contrasena_plana),
        )

    def _enviar(self, destinatario: str, asunto: str, html: str) -> bool:
        if not self._host:
            logger.warning("SMTP_HOST no configurado. Se omite el envio.")
            return False
        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{self._nombre} <{self._remitente}>"
        mensaje["To"] = destinatario
        mensaje.set_content("Abra este mensaje en un cliente compatible con HTML.")
        mensaje.add_alternative(html, subtype="html")
        try:
            with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
                if self._use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if self._user:
                    smtp.login(self._user, self._password)
                smtp.send_message(mensaje)
            return True
        except (smtplib.SMTPException, OSError) as err:
            logger.error("Fallo SMTP: %s", type(err).__name__)
            return False
