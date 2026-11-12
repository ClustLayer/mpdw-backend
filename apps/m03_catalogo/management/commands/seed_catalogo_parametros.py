# Semilla idempotente de parámetros del catálogo (tipos base, categoría y marca demo).
from django.core.management.base import BaseCommand

from apps.m03_catalogo.models import Categorias_producto, Marcas, Tipos_producto

TIPOS_BASE = (
    "Producto Terminado",
    "Materia Prima",
    "Insumo",
    "Combo/Promoción",
    "Servicio",
)


class Command(BaseCommand):
    help = "Asegura tipos base del catálogo y datos mínimos (Vinilos, Diana) para formularios de producto."

    def handle(self, *args, **options):
        for nombre in TIPOS_BASE:
            obj, created = Tipos_producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": "Tipo base",
                    "afecta_venta_diaria": True,
                    "es_base": True,
                    "estado": True,
                },
            )
            if not created:
                Tipos_producto.objects.filter(pk=obj.pk).update(es_base=True, estado=True)
            self.stdout.write(f"Tipo: {nombre}")

        Categorias_producto.objects.get_or_create(
            nombre="Vinilos",
            defaults={"descripcion": "Vinilos y recubrimientos decorativos", "estado": True},
        )
        Marcas.objects.get_or_create(
            nombre="Diana",
            defaults={"descripcion": "Marca Mundo Pinturas Diana", "estado": True},
        )
        self.stdout.write(self.style.SUCCESS("Parámetros de catálogo listos (tipos base, Vinilos, Diana)."))
