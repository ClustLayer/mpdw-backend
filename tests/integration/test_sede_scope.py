# ==============================================================================
# Prueba de Integración: Alcance por Sede en Autorización - MPDW
# SAD Ref: M01, ADR-007, TC-A13
# ==============================================================================
import pytest

from apps.m01_identidad.models import Roles, Usuario_sede, Usuarios
from apps.m01_identidad.repositories import UserRepository
from apps.m02_sedes.models import Sedes


@pytest.mark.django_db
@pytest.mark.integration
def test_empleado_sede_a_no_debe_tener_en_su_alcance_la_sede_b():
    # Arrange
    sede_a, _ = Sedes.objects.get_or_create(nombre="Sede A", defaults={"direccion": "Dir A"})
    sede_b, _ = Sedes.objects.get_or_create(nombre="Sede B", defaults={"direccion": "Dir B"})

    rol_emp, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True})
    empleado = Usuarios.objects.create_user(
        email="cajero@sedea.com",
        password="Password123!",
        nombre="Cajero A",
        documento="111222",
        id_rol=rol_emp,
    )

    Usuario_sede.objects.create(id_usuario=empleado, id_sede=sede_a, es_principal=True)

    repo = UserRepository()

    # Act
    sedes_autorizadas = repo.obtener_sedes_asignadas_ids(empleado.id_usuario)

    # Assert
    assert sede_a.id_sede in sedes_autorizadas
    assert sede_b.id_sede not in sedes_autorizadas

