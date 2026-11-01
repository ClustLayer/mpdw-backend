# ==============================================================================
# Implementación Django del Gestor de Transacciones - MPDW
# SAD Ref: ADR-005, K-11
# ==============================================================================
from collections.abc import Generator
from contextlib import contextmanager

from django.db import transaction

from contratos.puertos.transaccion import GestorTransaccionPort


class GestorTransaccionDjango(GestorTransaccionPort):
    """Implementa el puerto transaccional delegando en transaction.atomic de Django."""

    @contextmanager
    def atomic(self) -> Generator[None]:
        with transaction.atomic():
            yield

