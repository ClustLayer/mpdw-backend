"""Unit tests — PermissionRepository Sin acceso / Total."""

import pytest

from apps.m01_identidad.models import Permisos, Rol_permiso, Roles, Usuarios
from apps.m01_identidad.repositories import PermissionRepository
from apps.m01_identidad.services import PermissionService
from contratos.dtos import AuthContext


@pytest.mark.unit
@pytest.mark.django_db
def test_sin_acceso_bloquea_todas_las_acciones_del_modulo():
    rol = Roles.objects.get(nombre="Empleado")
    user = Usuarios.objects.create_user(
        email="sa@test.local",
        password="x",
        nombre="S",
        apellido="A",
        documento="900000004",
        id_rol=rol,
    )
    perm, _ = Permisos.objects.get_or_create(
        modulo="eventos",
        accion="Sin acceso",
        defaults={"nombre": "Eventos bloqueado", "estado": True},
    )
    Rol_permiso.objects.update_or_create(
        id_rol=rol, id_permiso=perm, defaults={"permitido": True}
    )
    repo = PermissionRepository()
    assert repo.tiene_permiso(user.id_usuario, rol.id_rol, "eventos", "Consultar") is False
    assert repo.acciones_por_modulo(user.id_usuario, rol.id_rol).get("eventos") == {"Sin acceso"}


@pytest.mark.unit
@pytest.mark.django_db
def test_accesos_panel_no_lista_modulo_sin_acceso():
    rol = Roles.objects.get(nombre="Empleado")
    user = Usuarios.objects.create_user(
        email="panel-sa@test.local",
        password="x",
        nombre="P",
        apellido="S",
        documento="900000005",
        id_rol=rol,
    )
    perm, _ = Permisos.objects.get_or_create(
        modulo="eventos",
        accion="Sin acceso",
        defaults={"nombre": "Eventos SA", "estado": True},
    )
    Rol_permiso.objects.update_or_create(
        id_rol=rol, id_permiso=perm, defaults={"permitido": True}
    )
    ctx = AuthContext(
        id_usuario=user.id_usuario,
        email=user.email,
        rol_nombre=rol.nombre,
        sedes_asignadas=(1,),
        es_global=False,
        id_rol=rol.id_rol,
        ip="127.0.0.1",
        user_agent="pytest",
        id_correlacion="c-sa",
    )
    data = PermissionService().accesos_panel(ctx)
    assert "eventos" not in data["modulos"]


@pytest.mark.unit
@pytest.mark.django_db
def test_accesos_panel_incluye_modulo_con_total():
    rol = Roles.objects.create(nombre="ConTotal", es_rol_base=False)
    user = Usuarios.objects.create_user(
        email="total@test.local",
        password="x",
        nombre="T",
        apellido="O",
        documento="900000006",
        id_rol=rol,
    )
    perm, _ = Permisos.objects.get_or_create(
        modulo="eventos",
        accion="Total",
        defaults={"nombre": "Eventos total", "estado": True},
    )
    Rol_permiso.objects.update_or_create(
        id_rol=rol, id_permiso=perm, defaults={"permitido": True}
    )
    ctx = AuthContext(
        id_usuario=user.id_usuario,
        email=user.email,
        rol_nombre=rol.nombre,
        sedes_asignadas=(1,),
        es_global=False,
        id_rol=rol.id_rol,
        ip="127.0.0.1",
        user_agent="pytest",
        id_correlacion="c-t",
    )
    data = PermissionService().accesos_panel(ctx)
    assert "eventos" in data["modulos"]
    assert "Total" in data["acciones_por_modulo"]["eventos"]
