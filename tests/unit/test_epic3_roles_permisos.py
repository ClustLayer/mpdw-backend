"""Unit tests Epic 3 — roles y permisos."""

from unittest.mock import MagicMock

import pytest

from apps.m01_identidad.admin_roles_permisos_service import AdminRolesPermisosService
from apps.m01_identidad.models import Permisos, Rol_permiso, Roles, Usuario_permiso, Usuarios
from apps.m01_identidad.services import PermissionService
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx_admin() -> AuthContext:
    return AuthContext(
        id_usuario=1,
        email="admin@test.local",
        rol_nombre="Administrador",
        sedes_asignadas=(1,),
        es_global=True,
        id_rol=1,
        ip="127.0.0.1",
        user_agent="pytest",
        id_correlacion="c1",
    )


@pytest.fixture
def svc() -> AdminRolesPermisosService:
    return AdminRolesPermisosService(audit_port=MagicMock())


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_rol_exito(svc, ctx_admin):
    _, msg = svc.crear_rol(ctx_admin, {"nombre": "Supervisor", "descripcion": "Apoyo"})
    assert "correctamente" in msg
    assert Roles.objects.filter(nombre="Supervisor").exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_detalle_rol(svc):
    rol = Roles.objects.get(nombre="Administrador")
    det = svc.detalle_rol(rol.id_rol)
    assert det["nombre"] == "Administrador"


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_rol_nombre_vacio(svc, ctx_admin):
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear_rol(ctx_admin, {"nombre": "  "})
    assert exc.value.codigo == "ROL_NOMBRE_OBLIGATORIO"


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_rol_duplicado(svc, ctx_admin):
    Roles.objects.create(nombre="Duplicado", es_rol_base=False)
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear_rol(ctx_admin, {"nombre": "duplicado"})
    assert exc.value.codigo == "ROL_NOMBRE_DUPLICADO"


@pytest.mark.unit
@pytest.mark.django_db
def test_editar_rol_base_bloqueado(svc, ctx_admin):
    rol = Roles.objects.get(nombre="Administrador")
    with pytest.raises(ReglaNegocioError) as exc:
        svc.editar_rol(ctx_admin, rol.id_rol, {"estado": False, "version_fila": rol.version_fila})
    assert exc.value.codigo == "ROL_BASE_PROTEGIDO"


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_permiso_duplicado_modulo_accion(svc, ctx_admin):
    Permisos.objects.create(nombre="P1", modulo="usuarios", accion="Crear", estado=True)
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear_permiso(
            ctx_admin,
            {"nombre": "P2", "modulo": "usuarios", "accion": "Crear"},
        )
    assert exc.value.codigo == "PERMISO_DUPLICADO"


@pytest.mark.unit
@pytest.mark.django_db
def test_matriz_usuario_override(ctx_admin, svc):
    rol = Roles.objects.get(nombre="Empleado")
    perm, _ = Permisos.objects.get_or_create(
        modulo="clientes",
        accion="Total",
        defaults={"nombre": "Clientes total", "estado": True},
    )
    user = Usuarios.objects.create_user(
        email="emp@test.local",
        password="x",
        nombre="E",
        apellido="M",
        documento="900000001",
        id_rol=rol,
    )
    svc.guardar_matriz(
        ctx_admin,
        {
            "tipo": "usuario",
            "id_destino": user.id_usuario,
            "cambios": [{"id_permiso": perm.id_permiso, "permitido": False}],
        },
    )
    ps = PermissionService()
    ok_ctx = AuthContext(
        id_usuario=user.id_usuario,
        email=user.email,
        rol_nombre=rol.nombre,
        sedes_asignadas=(1,),
        es_global=False,
        id_rol=rol.id_rol,
        ip="127.0.0.1",
        user_agent="pytest",
        id_correlacion="c2",
    )
    assert ps.tiene_permiso(ok_ctx, "clientes", "T") is False


@pytest.mark.unit
@pytest.mark.django_db
def test_eliminar_rol_custom_sin_usuarios(svc, ctx_admin):
    svc.crear_rol(ctx_admin, {"nombre": "Borrable", "descripcion": ""})
    rol = Roles.objects.get(nombre="Borrable")
    msg = svc.eliminar_rol(ctx_admin, rol.id_rol)
    assert "correctamente" in msg
    assert not Roles.objects.filter(pk=rol.id_rol).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_eliminar_rol_base_bloqueado(svc, ctx_admin):
    admin = Roles.objects.get(nombre="Administrador")
    with pytest.raises(ReglaNegocioError) as exc:
        svc.eliminar_rol(ctx_admin, admin.id_rol)
    assert exc.value.codigo == "ROL_BASE_PROTEGIDO"


@pytest.mark.unit
@pytest.mark.django_db
def test_eliminar_rol_con_usuario_asignado(svc, ctx_admin):
    rol = Roles.objects.create(nombre="NoBorrable", es_rol_base=False)
    Usuarios.objects.create_user(
        email="nb@test.local",
        password="x",
        nombre="N",
        apellido="B",
        documento="900000003",
        id_rol=rol,
    )
    with pytest.raises(ReglaNegocioError) as exc:
        svc.eliminar_rol(ctx_admin, rol.id_rol)
    assert exc.value.codigo == "ROL_USUARIOS_ASIGNADOS"


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_y_editar_rol_custom(svc, ctx_admin):
    svc.crear_rol(ctx_admin, {"nombre": "Auxiliar", "descripcion": ""})
    pag = svc.listar_roles("", "todos", 1, 20)
    assert pag.total >= 1
    rol = Roles.objects.get(nombre="Auxiliar")
    det, msg = svc.editar_rol(
        ctx_admin,
        rol.id_rol,
        {"descripcion": "Nueva desc", "version_fila": rol.version_fila},
    )
    assert det["descripcion"] == "Nueva desc"
    assert "correctamente" in msg


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_y_listar_permiso(svc, ctx_admin):
    _, msg = svc.crear_permiso(
        ctx_admin,
        {"nombre": "Exportar ventas", "modulo": "facturas", "accion": "Exportar", "descripcion": ""},
    )
    assert "correctamente" in msg
    pag = svc.listar_permisos("", "", "", "activo", 1, 50)
    assert any(p["accion"] == "Exportar" for p in pag.items)


@pytest.mark.unit
@pytest.mark.django_db
def test_inactivar_rol_con_usuarios_activos(svc, ctx_admin):
    rol = Roles.objects.create(nombre="ConUsuarios", es_rol_base=False, estado=True)
    emp = Roles.objects.get(nombre="Empleado")
    Usuarios.objects.create_user(
        email="u1@test.local",
        password="x",
        nombre="U",
        apellido="1",
        documento="900000002",
        id_rol=rol,
    )
    with pytest.raises(ReglaNegocioError) as exc:
        svc.editar_rol(ctx_admin, rol.id_rol, {"estado": False, "version_fila": rol.version_fila})
    assert exc.value.codigo == "ROL_USUARIOS_ACTIVOS"
    assert emp.nombre == "Empleado"


@pytest.mark.unit
@pytest.mark.django_db
def test_matriz_rol_y_catalogos(svc, ctx_admin):
    rol = Roles.objects.get(nombre="Gerente")
    data = svc.obtener_matriz("rol", rol.id_rol)
    assert data["tipo"] == "rol"
    assert len(data["filas"]) > 0
    cat = svc.catalogos()
    assert "modulos" in cat and "acciones" in cat
    assert "Sin acceso" in cat["acciones"]
    assert "Total" in cat["acciones"]


@pytest.mark.unit
@pytest.mark.django_db
def test_accesos_panel_admin(ctx_admin):
    data = PermissionService().accesos_panel(ctx_admin)
    assert "resumen" in data["modulos"]


@pytest.mark.unit
@pytest.mark.django_db
def test_accesos_panel_empleado():
    rol = Roles.objects.get(nombre="Empleado")
    ctx = AuthContext(
        id_usuario=99,
        email="e@test.local",
        rol_nombre="Empleado",
        sedes_asignadas=(1,),
        es_global=False,
        id_rol=rol.id_rol,
        ip="127.0.0.1",
        user_agent="pytest",
        id_correlacion="c3",
    )
    data = PermissionService().accesos_panel(ctx)
    assert isinstance(data["modulos"], list)


@pytest.mark.unit
@pytest.mark.django_db
def test_guardar_matriz_rol(svc, ctx_admin):
    rol = Roles.objects.create(nombre="MatrizRol", es_rol_base=False)
    perm = Permisos.objects.create(nombre="X", modulo="eventos", accion="Consultar", estado=True)
    msg = svc.guardar_matriz(
        ctx_admin,
        {"tipo": "rol", "id_destino": rol.id_rol, "cambios": [{"id_permiso": perm.id_permiso, "permitido": True}]},
    )
    assert "inmediato" in msg
    assert Rol_permiso.objects.filter(id_rol=rol, id_permiso=perm, permitido=True).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_editar_permiso_inactivar(svc, ctx_admin):
    perm = Permisos.objects.create(nombre="Tmp", modulo="eventos", accion="Anular", estado=True)
    _, msg = svc.editar_permiso(ctx_admin, perm.id_permiso, {"estado": False, "version_fila": perm.version_fila})
    assert "revocados" in msg or "correctamente" in msg


@pytest.mark.unit
@pytest.mark.django_db
def test_matriz_destino_invalido(svc):
    with pytest.raises(ReglaNegocioError):
        svc.obtener_matriz("otro", 1)


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_filtros_estado(svc, ctx_admin):
    Roles.objects.create(nombre="InactivoX", estado=False, es_rol_base=False)
    pag = svc.listar_roles("", "inactivo", 1, 50)
    assert all(not r["estado"] for r in pag.items)
    pag2 = svc.listar_permisos("", "usuarios", "", "todos", 1, 50)
    assert pag2.total >= 0


@pytest.mark.unit
@pytest.mark.django_db
def test_editar_rol_concurrencia(svc, ctx_admin):
    rol = Roles.objects.create(nombre="Conc", es_rol_base=False)
    with pytest.raises(ReglaNegocioError) as exc:
        svc.editar_rol(ctx_admin, rol.id_rol, {"descripcion": "x", "version_fila": 99})
    assert exc.value.codigo == "CONCURRENCIA"


@pytest.mark.unit
@pytest.mark.django_db
def test_matriz_usuario_eliminar_excepcion(svc, ctx_admin):
    rol = Roles.objects.get(nombre="Empleado")
    perm, _ = Permisos.objects.get_or_create(
        modulo="pos", accion="O", defaults={"nombre": "POS O", "estado": True}
    )
    user = Usuarios.objects.create_user(
        email="exc@test.local",
        password="x",
        nombre="E",
        apellido="X",
        documento="900000003",
        id_rol=rol,
    )
    Usuario_permiso.objects.create(id_usuario=user, id_permiso=perm, permitido=False)
    svc.guardar_matriz(
        ctx_admin,
        {
            "tipo": "usuario",
            "id_destino": user.id_usuario,
            "cambios": [{"id_permiso": perm.id_permiso, "permitido": True, "eliminar_excepcion": True}],
        },
    )
    assert not Usuario_permiso.objects.filter(id_usuario=user, id_permiso=perm).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_obtener_matriz_usuario(svc, ctx_admin):
    rol = Roles.objects.get(nombre="Empleado")
    user = Usuarios.objects.create_user(
        email="mat@test.local",
        password="x",
        nombre="M",
        apellido="U",
        documento="900000004",
        id_rol=rol,
    )
    data = svc.obtener_matriz("usuario", user.id_usuario)
    assert data["tipo"] == "usuario"
    assert len(data["filas"]) > 0


@pytest.mark.unit
@pytest.mark.django_db
def test_editar_permiso_duplicado(svc, ctx_admin):
    p1 = Permisos.objects.create(nombre="A", modulo="analitica", accion="Crear", estado=True)
    p2 = Permisos.objects.create(nombre="B", modulo="analitica", accion="Editar", estado=True)
    with pytest.raises(ReglaNegocioError):
        svc.editar_permiso(ctx_admin, p2.id_permiso, {"accion": "Crear", "version_fila": p2.version_fila})
    assert p1.accion == "Crear"


@pytest.mark.unit
@pytest.mark.django_db
def test_accesos_panel_sin_id_rol_en_ctx():
    ctx = AuthContext(
        id_usuario=1,
        email="x@test.local",
        rol_nombre="Empleado",
        sedes_asignadas=(1,),
        es_global=False,
        id_rol=None,
        ip="127.0.0.1",
        user_agent="pytest",
        id_correlacion="c4",
    )
    rol = Roles.objects.get(nombre="Empleado")
    Usuarios.objects.create_user(
        email="x@test.local",
        password="x",
        nombre="X",
        apellido="Y",
        documento="900000005",
        id_rol=rol,
    )
    data = PermissionService().accesos_panel(ctx)
    assert "modulos" in data
