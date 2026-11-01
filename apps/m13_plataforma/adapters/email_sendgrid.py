# ==============================================================================
# Adaptador Real SendGrid (HTTPX) - MPDW
# SAD Ref: E-02, I-07, §10.3
# ==============================================================================
import logging

import httpx
from django.conf import settings

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
                    "value": f"<p>Haga clic en el siguiente enlace para restablecer su contrasena: <a href='{enlace}'>{enlace}</a></p>",
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
            logger.error("Error SendGrid: %s - %s", response.status_code, response.text)
            return False
        except httpx.HTTPError as err:
            logger.error("Fallo de conexion con SendGrid: %s", err)
            return False
