# ==============================================================================
# Comando de Datos de Prueba para Desarrollo - MPDW
# SAD Ref: M03, §8.1, Q-12
# ==============================================================================
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.m03_catalogo.models import Categorias_producto, Marcas, Tipos_producto


class Command(BaseCommand):
    help = "Siembra datos de ejemplo para desarrollo local y pruebas del slice vertical (prohibido en produccion)."

    def handle(self, *args, **options):
        if not getattr(settings, "DEBUG", False):
            raise CommandError("seed_dev_data esta prohibido en produccion (DEBUG=False). Los catalogos reales son [Pendiente Q-12].")

        cat, _ = Categorias_producto.objects.get_or_create(
            id_categoria=1,
            defaults={"nombre": "Categoria Pruebas Dev", "descripcion": "Categoria de desarrollo", "estado": True},
        )
        marca, _ = Marcas.objects.get_or_create(
            id_marca=1,
            defaults={"nombre": "Marca Pruebas Dev", "estado": True},
        )
        tipo, _ = Tipos_producto.objects.get_or_create(
            id_tipo_producto=1,
            defaults={"nombre": "Tipo Pruebas Dev", "estado": True},
        )

        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence('\"Categorias_producto\"', 'id_categoria'), COALESCE((SELECT MAX(id_categoria) FROM \"Categorias_producto\"), 1));"
                    "SELECT setval(pg_get_serial_sequence('\"Marcas\"', 'id_marca'), COALESCE((SELECT MAX(id_marca) FROM \"Marcas\"), 1));"
                    "SELECT setval(pg_get_serial_sequence('\"Tipos_producto\"', 'id_tipo_producto'), COALESCE((SELECT MAX(id_tipo_producto) FROM \"Tipos_producto\"), 1));"
                )

        self.stdout.write(self.style.SUCCESS("Datos de desarrollo sembrados exitosamente (Categoria 1, Marca 1, Tipo 1)."))
