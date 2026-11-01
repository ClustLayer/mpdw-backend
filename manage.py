#!/usr/bin/env python
"""
manage.py - Entrypoint CLI para Mundo Pinturas Diana Web (MPDW)
SAD Ref: ADR-004, §6.6
"""
import os
import sys


def main() -> None:
    """Ejecutar tareas administrativas de Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Asegurate de que este instalado y "
            "disponible en tu variable de entorno PYTHONPATH."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

