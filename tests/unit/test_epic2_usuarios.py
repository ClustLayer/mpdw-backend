"""Pruebas unitarias Epic 2 - administracion de usuarios."""

from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.admin_usuarios_service import AdminUsuariosService
from apps.m01_identidad.mensajes import (
    MSG_CONTRASENA_TEMP_PROPIA,
    MSG_EMAIL_DUPLICADO,
    MSG_USUARIO_CREADO,
)
from apps.m01_identidad.models import Roles, Usuario_sede, Usuarios
from apps.m01_identidad.politicas import (
    documento_valido,
    generar_contrasena_inicial,
    telefono_valido,
)
from apps.m02_sedes.models import Sedes
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def admin_ctx(db) -> AuthContext:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    admin = Usuarios.objects.create_user(
        email="admin.epic2@test.local",
        password="Admin#2026demo",
        nombre="Admin",
        apellido="Epic2",
        documento="100001234567",
        id_rol=rol,
    )
    return AuthContext(
        id_usuario=admin.id_usuario,
        email=admin.email,
        rol_nombre="Administrador",
        sedes_asignadas=(),
        es_global=True,
        id_rol=rol.id_rol,
    )


@pytest.fixture
def sede_activa(db) -> Sedes:
    return Sedes.objects.create(nombre="Sede Test", direccion="Calle 1", ciudad="Cali", estado=True)


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_usuario_exige_campos(admin_ctx, sede_activa):
    servicio = AdminUsuariosService(email_port=FakeEmailAdapter())
    with pytest.raises(ReglaNegocioError, match="obligatorios"):
        servicio.crear(admin_ctx, {"nombre": "Ana"})


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_usuario_rechaza_email_duplicado(admin_ctx, sede_activa):
    rol = Roles.objects.get(nombre="Administrador")
    Usuarios.objects.create_user(
        email="dup@test.local",
        password="ClaveSegura#1",
        nombre="Existente",
        apellido="User",
        documento="100002345678",
        id_rol=rol,
    )
    servicio = AdminUsuariosService(email_port=FakeEmailAdapter())
    payload = {
        "nombre": "Nuevo",
        "apellido": "Usuario",
        "documento": "100003456789",
        "telefono": "3001234567",
        "email": "dup@test.local",
        "id_rol": rol.id_rol,
        "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
    }
    with pytest.raises(ReglaNegocioError, match=MSG_EMAIL_DUPLICADO):
        servicio.crear(admin_ctx, payload)


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_usuario_exitoso(admin_ctx, sede_activa):
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    email = FakeEmailAdapter()
    servicio = AdminUsuariosService(audit_port=MagicMock(), email_port=email)
    payload = {
        "nombre": "Laura",
        "apellido": "Perez",
        "documento": "100004567890",
        "telefono": "+573001112233",
        "email": "laura.perez@test.local",
        "id_rol": rol.id_rol,
        "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
    }
    mensaje, detalle = servicio.crear(admin_ctx, payload)
    assert mensaje == MSG_USUARIO_CREADO
    assert detalle["email"] == "laura.perez@test.local"
    assert Usuario_sede.objects.filter(id_usuario_id=detalle["id_usuario"], es_principal=True).exists()
    assert email.enviados


@pytest.mark.unit
@pytest.mark.django_db
def test_contrasena_temporal_no_en_cuenta_propia(admin_ctx):
    servicio = AdminUsuariosService()
    with pytest.raises(ReglaNegocioError, match=MSG_CONTRASENA_TEMP_PROPIA):
        servicio.generar_contrasena_temporal(admin_ctx, admin_ctx.id_usuario)


@pytest.mark.unit
def test_politicas_documento_y_telefono():
    assert documento_valido("ABC123456")
    assert not documento_valido("12")
    assert telefono_valido("+573001234567")
    assert not telefono_valido("30-abc")
    clave = generar_contrasena_inicial()
    assert len(clave) >= 12


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_y_cambiar_estado(admin_ctx, sede_activa):
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    email = FakeEmailAdapter()
    servicio = AdminUsuariosService(audit_port=MagicMock(), email_port=email)
    payload = {
        "nombre": "Pedro",
        "apellido": "Ruiz",
        "documento": "100005678901",
        "telefono": "",
        "email": "pedro.ruiz@test.local",
        "id_rol": rol.id_rol,
        "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
    }
    _, detalle = servicio.crear(admin_ctx, payload)
    pagina = servicio.listar("", None, "todos", 1, 20, "nombre")
    assert pagina.total >= 1
    msg = servicio.cambiar_estado(admin_ctx, detalle["id_usuario"], "desactivar")
    assert "actualizó" in msg


@pytest.mark.unit
@pytest.mark.django_db
def test_perfil_propio_actualiza_nombre(admin_ctx):
    from apps.m01_identidad.admin_usuarios_service import PerfilPropioService

    admin = Usuarios.objects.get(pk=admin_ctx.id_usuario)
    msg = PerfilPropioService(audit_port=MagicMock()).actualizar(
        admin_ctx,
        admin,
        {
            "nombre": "Admin",
            "apellido": "Epic2",
            "telefono": "3009998877",
            "tipo_sangre": "O+",
            "direccion": "Calle 10",
            "contacto_emergencia_nombre": "Contacto",
            "contacto_emergencia_telefono": "3001112233",
        },
    )
    assert "actualizado" in msg.lower()
    admin.refresh_from_db()
    assert admin.tipo_sangre == "O+"


@pytest.mark.unit
@pytest.mark.django_db
def test_actualizar_usuario_y_contrasena_temporal(admin_ctx, sede_activa):
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    servicio = AdminUsuariosService(audit_port=MagicMock(), email_port=FakeEmailAdapter())
    _, detalle = servicio.crear(
        admin_ctx,
        {
            "nombre": "Temp",
            "apellido": "User",
            "documento": "100008901234",
            "telefono": "",
            "email": "temp.user@test.local",
            "id_rol": rol.id_rol,
            "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
        },
    )
    mensaje, actualizado = servicio.actualizar(
        admin_ctx,
        detalle["id_usuario"],
        {
            "nombre": "Temp",
            "apellido": "Actualizado",
            "documento": "100008901234",
            "telefono": "3002223344",
            "email": "temp.user@test.local",
            "id_rol": rol.id_rol,
            "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
            "version_fila": detalle["version_fila"],
        },
    )
    assert "actualizado" in mensaje.lower()
    assert actualizado["apellido"] == "Actualizado"
    ok, clave = servicio.generar_contrasena_temporal(admin_ctx, detalle["id_usuario"])
    assert len(clave) >= 12
    assert "generada" in ok.lower()


@pytest.mark.unit
@pytest.mark.django_db
def test_api_usuarios_y_perfil(admin_ctx, sede_activa):
    admin = Usuarios.objects.get(pk=admin_ctx.id_usuario)
    from apps.m01_identidad.services import AuthService

    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        admin.email,
        "Admin#2026demo",
        "127.0.0.1",
        "pytest",
        "corr-api",
    )
    client = APIClient()
    assert login.access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/usuarios/roles").status_code == 200
    listado = client.get("/api/v1/usuarios/")
    assert listado.status_code == 200
    perfil = client.patch(
        "/api/v1/auth/profile",
        {"nombre": admin.nombre, "apellido": admin.apellido, "telefono": "3000000011"},
        format="json",
    )
    assert perfil.status_code == 200
    empleado, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    creado = client.post(
        "/api/v1/usuarios/",
        {
            "nombre": "Vista",
            "apellido": "Api",
            "documento": "100009012345",
            "telefono": "",
            "email": "vista.api@test.local",
            "id_rol": empleado.id_rol,
            "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
        },
        format="json",
    )
    assert creado.status_code == 201
    uid = creado.json()["id_usuario"]
    assert client.get(f"/api/v1/usuarios/{uid}").status_code == 200
    assert client.post(f"/api/v1/usuarios/{uid}/estado", {"accion": "bloquear"}, format="json").status_code == 200
    assert client.post(f"/api/v1/usuarios/{uid}/contrasena-temporal", {}, format="json").status_code == 200
    assert client.get("/api/v1/usuarios/999999").status_code == 404


@pytest.mark.unit
@pytest.mark.django_db
def test_listado_filtros_y_utilidades(admin_ctx, sede_activa):
    from apps.m01_identidad.usuario_util import estado_etiqueta, nombre_completo, snapshot_usuario

    servicio = AdminUsuariosService(audit_port=MagicMock(), email_port=FakeEmailAdapter())
    pagina = servicio.listar("Admin", None, "activo", 1, 10, "email")
    assert pagina.total >= 1
    admin = Usuarios.objects.get(pk=admin_ctx.id_usuario)
    assert nombre_completo(admin)
    assert estado_etiqueta(admin) == "Activo"
    assert snapshot_usuario(admin)["email"] == admin.email
    with pytest.raises(ReglaNegocioError):
        servicio.obtener_detalle(999999)


@pytest.mark.unit
@pytest.mark.django_db
def test_cambiar_estado_activar_y_bloquear(admin_ctx, sede_activa):
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    servicio = AdminUsuariosService(audit_port=MagicMock(), email_port=FakeEmailAdapter())
    _, detalle = servicio.crear(
        admin_ctx,
        {
            "nombre": "Estado",
            "apellido": "Flow",
            "documento": "100010123456",
            "telefono": "",
            "email": "estado.flow@test.local",
            "id_rol": rol.id_rol,
            "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
        },
    )
    uid = detalle["id_usuario"]
    servicio.cambiar_estado(admin_ctx, uid, "bloquear")
    servicio.cambiar_estado(admin_ctx, uid, "activar")
    servicio.cambiar_estado(admin_ctx, uid, "desactivar")
    pagina = servicio.listar("", None, "inactivo", 1, 20, "-ultimo_acceso")
    assert pagina.total >= 1


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.django_db
def test_crear_documento_duplicado(admin_ctx, sede_activa):
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    servicio = AdminUsuariosService(email_port=FakeEmailAdapter())
    base = {
        "nombre": "Dup",
        "apellido": "One",
        "documento": "100011234567",
        "telefono": "",
        "email": "dup.one@test.local",
        "id_rol": rol.id_rol,
        "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
    }
    servicio.crear(admin_ctx, base)
    base["email"] = "dup.two@test.local"
    with pytest.raises(ReglaNegocioError, match="documento"):
        servicio.crear(admin_ctx, base)


@pytest.mark.unit
@pytest.mark.django_db
def test_actualizar_concurrencia(admin_ctx, sede_activa):
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    servicio = AdminUsuariosService(audit_port=MagicMock(), email_port=FakeEmailAdapter())
    _, detalle = servicio.crear(
        admin_ctx,
        {
            "nombre": "Conc",
            "apellido": "User",
            "documento": "100012345678",
            "telefono": "",
            "email": "conc.user@test.local",
            "id_rol": rol.id_rol,
            "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
        },
    )
    with pytest.raises(ReglaNegocioError, match="modificado"):
        servicio.actualizar(
            admin_ctx,
            detalle["id_usuario"],
            {
                "nombre": "Conc",
                "apellido": "User",
                "documento": "100012345678",
                "telefono": "",
                "email": "conc.user@test.local",
                "id_rol": rol.id_rol,
                "sedes": [{"id_sede": sede_activa.id_sede, "es_principal": True}],
                "version_fila": 999,
            },
        )


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.django_db
def test_perfil_rechaza_cambio_de_rol(admin_ctx):
    from apps.m01_identidad.admin_usuarios_service import PerfilPropioService
    from apps.m01_identidad.mensajes import MSG_ROL_PROPIO

    admin = Usuarios.objects.get(pk=admin_ctx.id_usuario)
    with pytest.raises(ReglaNegocioError, match=MSG_ROL_PROPIO[:20]):
        PerfilPropioService().actualizar(admin_ctx, admin, {"nombre": "A", "apellido": "B", "telefono": "", "id_rol": 2})


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.django_db
def test_listado_vacio_y_accion_invalida(admin_ctx):
    servicio = AdminUsuariosService()
    vacio = servicio.listar("zzznomatch123", None, "activo", 1, 20, "nombre")
    assert vacio.total == 0
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    _, detalle = AdminUsuariosService(email_port=FakeEmailAdapter()).crear(
        admin_ctx,
        {
            "nombre": "Inv",
            "apellido": "Alid",
            "documento": "100013456789",
            "telefono": "",
            "email": "inv.alid@test.local",
            "id_rol": rol.id_rol,
            "sedes": [{"id_sede": Sedes.objects.create(nombre="S2", direccion="X", ciudad="Cali", estado=True).id_sede, "es_principal": True}],
        },
    )
    with pytest.raises(ReglaNegocioError):
        servicio.cambiar_estado(admin_ctx, detalle["id_usuario"], "invalida")


@pytest.mark.unit
def test_fake_email_contrasena_inicial():
    fake = FakeEmailAdapter()
    assert fake.enviar_contrasena_inicial("a@b.co", "Ana", "X") is True
    assert fake.enviados[-1]["tipo"] == "contrasena_inicial"


@pytest.mark.unit
def test_politicas_exigen_formato():
    from apps.m01_identidad.politicas import exigir_documento, exigir_telefono

    with pytest.raises(ReglaNegocioError):
        exigir_documento("bad")
    with pytest.raises(ReglaNegocioError):
        exigir_telefono("12-34")
