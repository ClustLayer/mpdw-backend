"""Selecciona SendGrid o SMTP segun el entorno. Nunca registra credenciales."""

from django.conf import settings

from apps.m13_plataforma.adapters.email_sendgrid import SendGridEmailAdapter
from apps.m13_plataforma.adapters.email_smtp import SmtpEmailAdapter
from contratos.puertos.correo import EmailPort


def construir_adaptador_correo() -> EmailPort:
    if getattr(settings, "SENDGRID_API_KEY", ""):
        return SendGridEmailAdapter()
    if getattr(settings, "SMTP_HOST", ""):
        return SmtpEmailAdapter()
    return SendGridEmailAdapter()
