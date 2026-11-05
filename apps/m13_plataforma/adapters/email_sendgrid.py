# ==============================================================================
# Adaptador Real SendGrid (HTTPX) - MPDW
# SAD Ref: E-02, I-07, §10.3
# ==============================================================================
import logging

import httpx
from django.conf import settings

from apps.m13_plataforma.adapters.plantillas_correo import html_codigo_2fa, html_recuperacion
from contratos.puertos.correo import EmailPort

logger = logging.getLogger(__name__)


class SendGridEmailAdapter(EmailPort):
    """Adaptador que interactúa con la API REST v3 de SendGrid usando httpx."""

    def __init__(
        self,
        api_key: str | None = None,
        remitente: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or getattr(settings, "SENDGRID_API_KEY", "")
        self._remitente = remitente or getattr(settings, "DEFAULT_FROM_EMAIL", "soporte@mundopinturasdiana.com")
        self._client = client or httpx.Client(timeout=10.0)

    def enviar_recuperacion_password(self, destinatario: str, enlace: str) -> bool:
        if not self._api_key:
            logger.warning("SENDGRID_API_KEY no configurada. Omitiendo envio a %s", destinatario)
            return False

        payload = {
            "personalizations": [
                {
                    "to": [{"email": destinatario}],
                    "subject": "Restablecer contrasena - Mundo Pinturas Diana",
                }
            ],
            "from": {"email": self._remitente, "name": "Mundo Pinturas Diana"},
            "content": [
                {
                    "type": "text/html",
                    "value": html_recuperacion(enlace),
                }
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = self._client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            if response.status_code in (200, 202):
                return True
            logger.error("Error SendGrid status %s", response.status_code)
            return False
        except httpx.HTTPError as err:
            logger.error("Fallo de conexion con SendGrid: %s", type(err).__name__)
            return False

    def enviar_codigo_2fa(self, destinatario: str, codigo: str) -> bool:
        if not self._api_key:
            logger.warning("SENDGRID_API_KEY no configurada. Omitiendo codigo 2FA.")
            return False
        payload = {
            "personalizations": [{"to": [{"email": destinatario}], "subject": "Codigo de verificacion - Mundo Pinturas Diana"}],
            "from": {"email": self._remitente, "name": "Mundo Pinturas Diana"},
            "content": [{"type": "text/html", "value": html_codigo_2fa(codigo)}],
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            response = self._client.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers, timeout=10.0)
            return response.status_code in (200, 202)
        except httpx.HTTPError as err:
            logger.error("Fallo de conexion con SendGrid: %s", type(err).__name__)
            return False
