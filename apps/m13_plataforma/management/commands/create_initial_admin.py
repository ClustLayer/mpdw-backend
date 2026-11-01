# ==============================================================================
# Comando de Creación del Primer Administrador - MPDW
# SAD Ref: BR-09, D6, §8.10
# ==============================================================================
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.m01_identidad.models import Roles, Usuario_sede, Usuarios
from apps.m02_sedes.models import Sedes


class Command(BaseCommand):
    help = "Crea el rol de Administrador y el primer usuario administrativo a partir de variables de entorno."

    def handle(self, *args, **options):
        email = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@mundopinturasdiana.com")
        password = os.environ.get("INITIAL_ADMIN_PASSWORD")
        if not password or "PLACEHOLDER" in password:
            raise CommandError("INITIAL_ADMIN_PASSWORD no esta configurada o contiene un placeholder invalido.")

        if len(password) < 10 or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
            raise CommandError("INITIAL_ADMIN_PASSWORD debe tener al menos 10 caracteres, una mayuscula y un digito.")

        nombre = os.environ.get("INITIAL_ADMIN_NAME", "Administrador Inicial MPDW")

        with transaction.atomic():
            # 1. Asegurar roles base protegidos (SAD §4.1, BR-10, Anexo A)
            admin_rol, _ = Roles.objects.get_or_create(
                nombre="Administrador",
                defaults={"descripcion": "Acceso total al backoffice", "es_rol_base": True, "estado": True},
            )
            Roles.objects.get_or_create(
                nombre="Gerente",
                defaults={"descripcion": "Supervision de ventas, caja e inventario", "es_rol_base": True, "estado": True},
            )
            Roles.objects.get_or_create(
                nombre="Empleado",
                defaults={"descripcion": "Operacion POS, ventas y caja", "es_rol_base": True, "estado": True},
            )

            # 2. Asegurar al menos una sede principal de arranque (SAD §8.1, RI-25)
            sede_principal, _ = Sedes.objects.get_or_create(
                nombre="Sede Principal",
                defaults={
                    "direccion": "Calle 10 # 5-20",
                    "telefono": "3001234567",
                    "ciudad": "Bogota",
                    "estado": True,
                },
            )

            # 3. Crear usuario administrador inicial
            if Usuarios.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f"El usuario admin {email} ya existe."))
                return

            usuario = Usuarios(
                email=email,
                nombre=nombre,
                documento="0000000000",
                id_rol=admin_rol,
                estado=True,
            )
            usuario.set_password(password)
            usuario.save()

            # 4. Asignar sede principal
            Usuario_sede.objects.create(
                id_usuario=usuario,
                id_sede=sede_principal,
                es_principal=True,
                estado=True,
            )

            self.stdout.write(self.style.SUCCESS(f"Administrador inicial '{email}' creado exitosamente."))

