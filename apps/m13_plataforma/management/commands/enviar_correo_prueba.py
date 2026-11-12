"""Envía un correo de prueba SMTP (solo entornos con credenciales configuradas)."""

import os

from django.core.management.base import BaseCommand, CommandError

from apps.m13_plataforma.adapters.correo_factory import construir_adaptador_correo


class Command(BaseCommand):
    help = "Envía un correo de prueba al destinatario indicado en CORREO_PRUEBA_DESTINO."

    def handle(self, *args, **options):
        destino = os.environ.get("CORREO_PRUEBA_DESTINO", "").strip()
        if not destino:
            raise CommandError("Defina CORREO_PRUEBA_DESTINO en el entorno.")
        frontend = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        enlace = f"{frontend}/nueva-contrasena#rt=prueba-canal-correo"
        adaptador = construir_adaptador_correo()
        ok = adaptador.enviar_recuperacion_password(destino, enlace)
        if not ok:
            raise CommandError("No fue posible enviar el correo de prueba. Revise SMTP_* en el entorno.")
        self.stdout.write(self.style.SUCCESS(f"Correo de prueba enviado a {destino}."))
