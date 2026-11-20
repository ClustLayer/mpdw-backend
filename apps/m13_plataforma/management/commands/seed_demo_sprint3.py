"""Semilla de ventas y domicilios de ejemplo (solo DEBUG)."""

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m05_clientes.models import Clientes, Tipos_cliente
from apps.m06_ventas.models import Facturas, Metodos_pago, Tipos_venta
from apps.m07_domicilios.models import Entregas, Mensajeros
from contratos.dtos import AuthContext


class Command(BaseCommand):
    help = "Genera facturas y domicilios de muestra para pruebas manuales (Sprint 3)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Solo disponible con DEBUG=True.")

        if Facturas.objects.count() >= 15:
            self.stdout.write("Ya hay suficientes facturas de ejemplo; omitiendo.")
            return

        rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
        user = Usuarios.objects.filter(email="admin@mpdw.local").first()
        if not user:
            user = Usuarios.objects.create_user(
                email="admin@mpdw.local",
                password="Admin#2026demo",
                nombre="Admin",
                apellido="Demo",
                documento="900000001",
                id_rol=rol,
            )
        ctx = AuthContext(user.id_usuario, user.email, "Administrador", (), True, id_rol=rol.id_rol, ip="127.0.0.1")

        sede, _ = Sedes.objects.get_or_create(
            nombre="Sede Demo Ventas",
            defaults={"direccion": "Calle 100", "estado": True, "ciudad": "BOG"},
        )
        tipo_cli, _ = Tipos_cliente.objects.get_or_create(
            nombre="Común",
            defaults={"estado": True, "es_tipo_predeterminado": True},
        )
        tipo_dom, _ = Tipos_venta.objects.get_or_create(nombre="Domicilio", defaults={"estado": True})
        tipo_most, _ = Tipos_venta.objects.get_or_create(nombre="Mostrador", defaults={"estado": True})
        Metodos_pago.objects.get_or_create(nombre="Efectivo", defaults={"estado": True})

        clientes = []
        for i in range(1, 6):
            c, _ = Clientes.objects.get_or_create(
                documento=f"DEMO-CLI-{i:03d}",
                defaults={
                    "nombre": f"Cliente",
                    "apellido": f"Demo {i}",
                    "numero_telefono": f"+57300{i:07d}",
                    "direccion": f"Carrera {i} # 10-20",
                    "ciudad": "Bogotá",
                    "id_tipo_cliente": tipo_cli,
                    "estado": True,
                },
            )
            clientes.append(c)

        mensajero, _ = Mensajeros.objects.get_or_create(
            documento="DOM-RIDER-01",
            defaults={
                "nombre": "Pedro",
                "apellido": "Repartidor",
                "telefono": "3005556677",
                "fecha_inicio": timezone.localdate(),
                "estado": True,
            },
        )

        estados_entrega = ["PENDIENTE", "ASIGNADO", "EN_CAMINO", "ENTREGADO", "CANCELADO"]
        for i in range(12):
            es_dom = i % 2 == 0
            f = Facturas.objects.create(
                id_sede=sede,
                serie="D",
                numero_factura=f"{1000 + i:04d}",
                id_cliente=clientes[i % len(clientes)],
                id_usuario=user,
                id_tipo_venta=tipo_dom if es_dom else tipo_most,
                subtotal=Decimal("50000") + i * 5000,
                total=Decimal("50000") + i * 5000,
                estado="EMITIDA",
                requiere_domicilio=es_dom,
            )
            if es_dom and i < 8:
                estado = estados_entrega[i % len(estados_entrega)]
                Entregas.objects.get_or_create(
                    id_factura=f,
                    defaults={
                        "direccion": clientes[i % len(clientes)].direccion,
                        "telefono_contacto": clientes[i % len(clientes)].numero_telefono,
                        "valor_cobrado_cliente": Decimal("8000"),
                        "valor_pagado_mensajero": Decimal("5000"),
                        "estado": estado,
                        "id_mensajero": mensajero if estado != "PENDIENTE" else None,
                    },
                )

        self.stdout.write(self.style.SUCCESS(f"Semilla Sprint 3 aplicada (usuario {user.email}, sede {sede.nombre})."))
        _ = ctx  # reservado para futura emisión vía servicio