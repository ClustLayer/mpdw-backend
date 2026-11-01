# ==============================================================================
# Comando de Gestión ETL - Agregación Analítica - MPDW
# SAD Ref: ADR-013, §7.5, §8.11
# ==============================================================================
import time
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Ejecuta el proceso por lotes de agregacion analitica hacia el esquema analitica (SAD ADR-013)."

    def add_arguments(self, parser):
        parser.add_argument("--desde", type=str, help="Fecha inicio en formato AAAA-MM-DD")
        parser.add_argument("--hasta", type=str, help="Fecha fin en formato AAAA-MM-DD")

    def handle(self, *args, **options):
        # Determinar rango de fechas a procesar (por defecto: ultimos 7 dias en America/Bogota)
        hoy = timezone.localdate()
        fecha_desde = date.fromisoformat(options["desde"]) if options.get("desde") else (hoy - timedelta(days=7))
        fecha_hasta = date.fromisoformat(options["hasta"]) if options.get("hasta") else hoy

        self.stdout.write(f"Iniciando proceso ETL para el periodo: {fecha_desde} a {fecha_hasta}...")
        tiempo_inicio = time.time()
        fecha_inicio_dt = timezone.now()

        # Usar la conexión directa/sesión para ETL
        db_alias = "direct" if "direct" in connections else "default"

        with transaction.atomic(using=db_alias):
            with connections[db_alias].cursor() as cursor:
                # 1. Adquirir bloqueo asesor transaccional para evitar corridas solapadas (ADR-013)
                cursor.execute("SELECT pg_try_advisory_xact_lock(424242);")
                bloqueo_obtenido = cursor.fetchone()[0]

                if not bloqueo_obtenido:
                    self.stdout.write(self.style.WARNING("Otra corrida del ETL ya esta en ejecucion. Finalizando."))
                    return

                # 2. Fijar timeout local de ejecucion
                cursor.execute("SET LOCAL statement_timeout = '120s';")

                total_filas = 0
                try:
                    # 3. Agregación de ventas diarias por sede (INSERT ... ON CONFLICT DO UPDATE)
                    cursor.execute(
                        """
                        INSERT INTO analitica.ventas_diarias (fecha, id_sede, total_ventas, cantidad_facturas, fecha_calculo)
                        SELECT
                            (fecha_hora AT TIME ZONE 'America/Bogota')::DATE AS fecha,
                            id_sede,
                            COALESCE(SUM(total), 0) AS total_ventas,
                            COUNT(id_factura) AS cantidad_facturas,
                            NOW()
                        FROM "Facturas"
                        WHERE estado = 'EMITIDA'
                          AND (fecha_hora AT TIME ZONE 'America/Bogota')::DATE BETWEEN %s AND %s
                        GROUP BY 1, 2
                        ON CONFLICT (fecha, id_sede) DO UPDATE
                        SET total_ventas = EXCLUDED.total_ventas,
                            cantidad_facturas = EXCLUDED.cantidad_facturas,
                            fecha_calculo = NOW();
                        """,
                        [fecha_desde, fecha_hasta],
                    )
                    total_filas += cursor.rowcount

                    # 4. Alertas de inventario crítico (menos de 5 unidades)
                    cursor.execute(
                        """
                        INSERT INTO analitica.inventario_alerta (fecha, id_producto, id_sede, cantidad_actual, nivel_alerta, fecha_calculo)
                        SELECT
                            CURRENT_DATE,
                            id_producto,
                            id_sede,
                            cantidad_actual,
                            'CRITICO',
                            NOW()
                        FROM "Inventarios"
                        WHERE cantidad_actual <= 5;
                        """
                    )
                    total_filas += cursor.rowcount

                    duracion = round(time.time() - tiempo_inicio, 2)

                    # 5. Registrar telemetría de corrida exitosa
                    cursor.execute(
                        """
                        INSERT INTO analitica.corrida_etl (fecha_inicio, fecha_fin, estado, filas_afectadas, duracion_segundos)
                        VALUES (%s, NOW(), 'EXITO', %s, %s);
                        """,
                        [fecha_inicio_dt, total_filas, duracion],
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"ETL finalizado con EXITO en {duracion}s. Filas procesadas/actualizadas: {total_filas}."
                        )
                    )

                except Exception as exc:
                    duracion = round(time.time() - tiempo_inicio, 2)
                    cursor.execute(
                        """
                        INSERT INTO analitica.corrida_etl (fecha_inicio, fecha_fin, estado, filas_afectadas, mensaje_error, duracion_segundos)
                        VALUES (%s, NOW(), 'ERROR', %s, %s, %s);
                        """,
                        [fecha_inicio_dt, total_filas, str(exc), duracion],
                    )
                    self.stdout.write(self.style.ERROR(f"Error durante corrida ETL: {exc}"))
                    raise exc

