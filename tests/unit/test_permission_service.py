# ==============================================================================
# Pruebas Unitarias: Evaluación de Autorización - MPDW
# SAD Ref: M01, ADR-007, BR-10, QA-05
# ==============================================================================
from unittest.mock import MagicMock, patch

import pytest

from apps.m01_identidad.services import PermissionService
from contratos.dtos import AuthContext


class FakePermissionRepo:
    def __init__(self, overrides: dict | None = None, role_perms: set | None = None) -> None:
        self.overrides = overrides or {}  # (id_usuario, modulo, accion) -> bool
        self.role_perms = role_perms or set()  # (id_rol, modulo, accion)

    def tiene_permiso(self, id_usuario: int, id_rol: int, modulo: str, accion: str) -> bool:
        # 1. Verificar override individual (Usuario_permiso)
        if (id_usuario, modulo, accion) in self.overrides:
            return self.overrides[(id_usuario, modulo, accion)]
        # 2. Verificar rol base (Rol_permiso)
        if (id_rol, modulo, accion) in self.role_perms:
            return True
        # 3. Deny by default
        return False


@pytest.mark.unit
def test_administrador_global_tiene_acceso_irrestricto():
    service = PermissionService()
    ctx = AuthContext(
        id_usuario=1,
        email="admin@diana.com",
        rol_nombre="Administrador",
        sedes_asignadas=(1,),
        es_global=True,
    )
    assert service.tiene_permiso(ctx, "m01_identidad", "crear") is True


@pytest.mark.unit
def test_permission_service_consulta_repositorio():
    repo_mock = MagicMock()
    repo_mock.tiene_permiso.return_value = True

    service = PermissionService(repo=repo_mock)
    ctx = AuthContext(
        id_usuario=20,
        email="cajero@diana.com",
        rol_nombre="Cajero",
        sedes_asignadas=(1,),
        es_global=False,
    )

    fake_user = MagicMock()
    fake_user.id_rol_id = 2

    with patch("apps.m01_identidad.models.Usuarios.objects.only") as mock_only:
        mock_only.return_value.get.return_value = fake_user
        tiene = service.tiene_permiso(ctx, "m08_caja", "abrir")

    assert tiene is True
    repo_mock.tiene_permiso.assert_called_once_with(20, 2, "m08_caja", "abrir")


@pytest.mark.unit
def test_permission_service_retorna_false_si_usuario_no_existe():
    service = PermissionService()
    ctx = AuthContext(
        id_usuario=999,
        email="inexistente@diana.com",
        rol_nombre="Cajero",
        sedes_asignadas=(),
        es_global=False,
    )
    with patch("apps.m01_identidad.models.Usuarios.objects.only") as mock_only:
        mock_only.return_value.get.side_effect = Exception("User not found")
        tiene = service.tiene_permiso(ctx, "m08_caja", "abrir")

    assert tiene is False


@pytest.mark.unit
def test_debe_permitir_cuando_rol_tiene_el_permiso():
    repo = FakePermissionRepo(role_perms={(2, "VENTAS", "EMITIR_FACTURA")})
    assert repo.tiene_permiso(id_usuario=10, id_rol=2, modulo="VENTAS", accion="EMITIR_FACTURA") is True


@pytest.mark.unit
def test_debe_denegar_por_defecto_si_no_existe_asignacion():
    repo = FakePermissionRepo()
    assert repo.tiene_permiso(id_usuario=10, id_rol=3, modulo="CAJA", accion="CERRAR_JORNADA") is False


@pytest.mark.unit
def test_debe_prevalecer_excepcion_individual_que_concede_permiso():
    repo = FakePermissionRepo(
        overrides={(15, "CAJA", "REABRIR_JORNADA"): True},
        role_perms=set(),
    )
    assert repo.tiene_permiso(id_usuario=15, id_rol=3, modulo="CAJA", accion="REABRIR_JORNADA") is True


@pytest.mark.unit
def test_debe_prevalecer_excepcion_individual_que_deniega_permiso():
    repo = FakePermissionRepo(
        overrides={(15, "VENTAS", "EMITIR_FACTURA"): False},
        role_perms={(2, "VENTAS", "EMITIR_FACTURA")},
    )
    assert repo.tiene_permiso(id_usuario=15, id_rol=2, modulo="VENTAS", accion="EMITIR_FACTURA") is False
