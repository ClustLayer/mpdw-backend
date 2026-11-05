# ==============================================================================
# Usuarios de demostración por rol (solo entornos controlados vía variables de entorno)
# SAD Ref: BR-09, §8.10
# ==============================================================================
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.m01_identidad.models import Roles, Usuario_sede, Usuarios
from apps.m02_sedes.models import Sedes


def _password_ok(password: str) -> bool:
    return (
        bool(password)
        and "PLACEHOLDER" not in password
        and len(password) >= 10
        and any(c.isupper() for c in password)
        and any(c.isdigit() for c in password)
    )


class Command(BaseCommand):
    help = (
        "Crea usuarios de ejemplo por rol (Administrador, Gerente, Empleado) "
        "usando contraseñas definidas solo en variables de entorno."
    )

    def handle(self, *args, **options):
        specs = [
            ("Administrador", "DEMO_ADMIN_EMAIL", "DEMO_ADMIN_PASSWORD", "DEMO_ADMIN_NAME", "9000000001"),
            ("Gerente", "DEMO_GERENTE_EMAIL", "DEMO_GERENTE_PASSWORD", "DEMO_GERENTE_NAME", "9000000002"),
            ("Empleado", "DEMO_EMPLEADO_EMAIL", "DEMO_EMPLEADO_PASSWORD", "DEMO_EMPLEADO_NAME", "9000000003"),
        ]
        defaults = {
            "DEMO_ADMIN_EMAIL": "admin.demo@mundopinturasdiana.com",
            "DEMO_GERENTE_EMAIL": "gerente.demo@mundopinturasdiana.com",
            "DEMO_EMPLEADO_EMAIL": "empleado.demo@mundopinturasdiana.com",
            "DEMO_ADMIN_NAME": "Admin Demo Epic1",
            "DEMO_GERENTE_NAME": "Gerente Demo Epic1",
            "DEMO_EMPLEADO_NAME": "Empleado Demo Epic1",
        }

        with transaction.atomic():
            sede_principal, _ = Sedes.objects.get_or_create(
                nombre="Sede Principal",
                defaults={
                    "direccion": "Calle 10 # 5-20",
                    "telefono": "3001234567",
                    "ciudad": "Bogota",
                    "estado": True,
                },
            )

            for rol_nombre, email_key, pass_key, name_key, documento in specs:
                email = os.environ.get(email_key, defaults[email_key])
                password = os.environ.get(pass_key, "")
                nombre = os.environ.get(name_key, defaults[name_key])
                if not _password_ok(password):
                    raise CommandError(f"{pass_key} no esta configurada o no cumple la politica minima.")

                rol, _ = Roles.objects.get_or_create(
                    nombre=rol_nombre,
                    defaults={"descripcion": f"Rol {rol_nombre}", "es_rol_base": True, "estado": True},
                )

                usuario, created = Usuarios.objects.get_or_create(
                    email=email,
                    defaults={
                        "nombre": nombre,
                        "documento": documento,
                        "id_rol": rol,
                        "estado": True,
                    },
                )
                if created:
                    usuario.set_password(password)
                    usuario.save()
                    Usuario_sede.objects.create(
                        id_usuario=usuario,
                        id_sede=sede_principal,
                        es_principal=True,
                        estado=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Creado {rol_nombre}: {email}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Ya existia {email}; no se modifico la contraseña."))
