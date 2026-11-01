# ==============================================================================
# Prueba de Integración: Inmutabilidad de Auditoría - MPDW
# SAD Ref: M10, ADR-008, RI-16, QA-08
# ==============================================================================
import pytest
from django.db import DatabaseError, connection, transaction

from apps.m10_auditoria.models import Auditoria


@pytest.mark.django_db
@pytest.mark.integration
def test_auditoria_debe_registrar_y_rechazar_modificacion_o_borrado():
    # Arrange
    auditoria = Auditoria.objects.create(
        accion="PRUEBA_INMUTABILIDAD",
        entidad="Productos",
        id_entidad=10,
        motivo="Prueba de trigger",
        resultado="EXITO",
    )
    assert auditoria.id_auditoria is not None

    # En bases de datos PostgreSQL con el trigger trg_auditoria_inmutable activo:
    if connection.vendor == "postgresql":
        # Act & Assert 1: Intento de UPDATE debe ser rechazado
        with pytest.raises(DatabaseError) as exc_update:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        'UPDATE "Auditoria" SET motivo = %s WHERE id_auditoria = %s',
                        ["Intento de alteracion", auditoria.id_auditoria],
                    )
        assert "Violacion de inmutabilidad (RI-16)" in str(exc_update.value)

        # Act & Assert 2: Intento de DELETE debe ser rechazado
        with pytest.raises(DatabaseError) as exc_delete:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        'DELETE FROM "Auditoria" WHERE id_auditoria = %s',
                        [auditoria.id_auditoria],
                    )
        assert "Violacion de inmutabilidad (RI-16)" in str(exc_delete.value)

