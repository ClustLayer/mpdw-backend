"""Job de archivo bimestral (informe §3): exportar → verificar → no borrar por defecto."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.m13_plataforma.observability.archive_job import ejecutar_archivo, periodo_cerrado_anterior


class Command(BaseCommand):
    help = (
        "Exporta logs del periodo bimestral cerrado a JSONL.gz + manifiesto SHA-256. "
        "No elimina datos operativos (backup ≠ borrado)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra el periodo que se archivaría.",
        )
        parser.add_argument(
            "--sin-contingencia",
            action="store_true",
            help="No incluir media/backups/auditoria_migracion_backup.jsonl.",
        )

    def handle(self, *args, **options):
        periodo = periodo_cerrado_anterior()
        if options["dry_run"]:
            self.stdout.write(
                self.style.NOTICE(
                    f"Periodo a archivar: {periodo.etiqueta} "
                    f"[{periodo.inicio.isoformat()} .. {periodo.fin.isoformat()})"
                )
            )
            return
        manifiesto = ejecutar_archivo(incluir_contingencia_local=not options["sin_contingencia"])
        self.stdout.write(self.style.SUCCESS(json.dumps(manifiesto, ensure_ascii=False, indent=2)))
