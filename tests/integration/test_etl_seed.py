# ==============================================================================
# Prueba de Integración: Corrida del ETL sobre Semillas - MPDW
# SAD Ref: ADR-013, §8.11, §14.2
# ==============================================================================
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import connection

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Categorias_producto, Productos
from apps.m04_inventario.models import Inventarios
from apps.m05_clientes.models import Clientes, Tipos_cliente
from apps.m06_ventas.models import Facturas, Tipos_venta


@pytest.mark.django_db(transaction=True, databases=["default", "direct"])
@pytest.mark.integration
def test_corrida_etl_sobre_semilla_puebla_esquema_analitica():
    """
    SAD §14.2: Una corrida del ETL sobre semilla produce las filas de §8.11
    en analitica.ventas_diarias, analitica.inventario_alerta y analitica.corrida_etl.
    """
    if connection.vendor != "postgresql":
        pytest.skip("Prueba de ETL requiere PostgreSQL con esquema analitica.")

    # 1. Arrange: Semilla de datos operacionales
    sede, _ = Sedes.objects.get_or_create(nombre="Sede ETL", defaults={"direccion": "Calle 50"})
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True})
    user, _ = Usuarios.objects.get_or_create(
        email="admin_etl@mpdw.com",
        defaults={"nombre": "Admin ETL", "documento": "11223344", "id_rol": rol},
    )
    tipo_cli, _ = Tipos_cliente.objects.get_or_create(nombre="Persona Natural")
    cliente, _ = Clientes.objects.get_or_create(
        documento="900123456",
        defaults={
            "nombre": "Cliente ETL S.A.S.",
            "numero_telefono": "+573001112233",
            "id_tipo_cliente": tipo_cli,
        },
    )
    cat, _ = Categorias_producto.objects.get_or_create(nombre="Esmaltes ETL")
    producto, _ = Productos.objects.get_or_create(
        codigo_producto="PROD-ETL-01",
        defaults={
            "nombre": "Esmalte Brillante",
            "precio_venta": Decimal("35000.00"),
            "id_categoria": cat,
            "version": 1,
        },
    )

    # Inventario crítico (3 unidades <= 5)
    Inventarios.objects.update_or_create(
        id_producto=producto,
        id_sede=sede,
        defaults={"cantidad_actual": Decimal("3.00"), "cantidad_reservada": Decimal("0.00")},
    )

    # Factura emitida hoy
    tipo_venta, _ = Tipos_venta.objects.get_or_create(nombre="POS")
    Facturas.objects.create(
        serie="A",
        numero_factura=1,
        id_sede=sede,
        id_usuario=user,
        id_cliente=cliente,
        id_tipo_venta=tipo_venta,
        subtotal=Decimal("70000.00"),
        impuesto=Decimal("13300.00"),
        total=Decimal("83300.00"),
        estado="EMITIDA",
    )

    # 2. Act: Ejecutar comando ETL
    call_command("run_etl")

    # 3. Assert: Verificar datos agregados en el esquema analitica
    with connection.cursor() as cursor:
        # a) Ventas diarias agregadas
        cursor.execute(
            "SELECT total_ventas, cantidad_facturas FROM analitica.ventas_diarias WHERE id_sede = %s;",
            [sede.id_sede],
        )
        row_ventas = cursor.fetchone()
        assert row_ventas is not None, "No se generó fila en analitica.ventas_diarias"
        assert Decimal(row_ventas[0]) == Decimal("83300.00")
        assert row_ventas[1] >= 1

        # b) Alertas de inventario crítico
        cursor.execute(
            "SELECT cantidad_actual, nivel_alerta FROM analitica.inventario_alerta WHERE id_producto = %s AND id_sede = %s;",
            [producto.id_producto, sede.id_sede],
        )
        row_alerta = cursor.fetchone()
        assert row_alerta is not None, "No se generó alerta en analitica.inventario_alerta"
        assert Decimal(row_alerta[0]) == Decimal("3.00")
        assert row_alerta[1] == "CRITICO"

        # c) Telemetría de corrida
        cursor.execute(
            "SELECT estado FROM analitica.corrida_etl ORDER BY id_corrida DESC LIMIT 1;"
        )
        row_corrida = cursor.fetchone()
        assert row_corrida is not None
        assert row_corrida[0] == "EXITO"
