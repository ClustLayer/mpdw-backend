import pytest

from apps.m10_auditoria.bitacora_service import BitacoraAuditoriaService
from apps.m10_auditoria.models import Auditoria
from contratos.excepciones import DominioError, ReglaNegocioError


@pytest.mark.unit
@pytest.mark.django_db
def test_listar_vacio_mensaje():
    svc = BitacoraAuditoriaService()
    pag = svc.listar({})
    assert pag.total == 0
    assert "criterios" in pag.mensaje


@pytest.mark.unit
@pytest.mark.django_db
def test_filtro_invalido_pagina():
    svc = BitacoraAuditoriaService()
    with pytest.raises(DominioError) as exc:
        svc.listar({"page": "x"})
    assert exc.value.codigo == "PAGINACION_INVALIDA"


@pytest.mark.unit
@pytest.mark.django_db
def test_rango_fecha_invalido():
    svc = BitacoraAuditoriaService()
    with pytest.raises(ReglaNegocioError):
        svc.listar({"fecha_desde": "2025-01-10", "fecha_hasta": "2025-01-01"})


@pytest.mark.unit
@pytest.mark.django_db
def test_una_fila_resumen():
    Auditoria.objects.create(
        id_usuario_id=None,
        accion="LOGIN_EXITOSO",
        motivo="Inicio de sesión",
        ip="192.168.1.1",
    )
    svc = BitacoraAuditoriaService()
    pag = svc.listar({})
    assert pag.total == 1
    assert "1 de 1" in pag.mensaje
    assert pag.items[0]["resumen"]
    assert "entidad" not in pag.items[0]


@pytest.mark.unit
@pytest.mark.django_db
def test_opciones_usuarios():
    from apps.m01_identidad.models import Roles, Usuarios

    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    Usuarios.objects.create_user(
        email="busq.bit@test.local",
        password="x",
        nombre="Busq",
        apellido="Bit",
        documento="911111111",
        id_rol=rol,
    )
    svc = BitacoraAuditoriaService()
    opts = svc.opciones_usuarios("Busq", limit=5)
    assert any("Busq" in o["etiqueta"] for o in opts)


@pytest.mark.unit
@pytest.mark.django_db
def test_resumen_sin_json():
    Auditoria.objects.create(
        id_usuario_id=None,
        accion="LOGIN_FALLIDO",
        motivo="—",
        ip="::1",
    )
    pag = BitacoraAuditoriaService().listar({})
    assert pag.items[0]["resumen"] == "—"


@pytest.mark.unit
@pytest.mark.django_db
def test_parse_fecha_iso_con_z():
    Auditoria.objects.create(
        id_usuario_id=None,
        accion="CAMBIO_PASSWORD",
        motivo="—",
        ip="127.0.0.1",
    )
    svc = BitacoraAuditoriaService()
    pag = svc.listar({"fecha_desde": "2020-01-01T00:00:00Z", "fecha_hasta": "2030-12-31T23:59:59Z"})
    assert pag.total >= 1


@pytest.mark.unit
@pytest.mark.django_db
def test_fecha_invalida():
    svc = BitacoraAuditoriaService()
    with pytest.raises(DominioError) as exc:
        svc.listar({"fecha_desde": "no-es-fecha"})
    assert exc.value.codigo == "FECHAS_INVALIDAS"


@pytest.mark.unit
@pytest.mark.django_db
def test_resumen_desde_motivo():
    Auditoria.objects.create(
        id_usuario_id=None,
        accion="LOGIN_EXITOSO",
        motivo="Ajuste manual de sede Norte",
        ip="10.0.0.1",
    )
    pag = BitacoraAuditoriaService().listar({})
    assert "Ajuste manual" in pag.items[0]["resumen"]


@pytest.mark.unit
@pytest.mark.django_db
def test_filtros_accion_y_usuario():
    from apps.m01_identidad.models import Roles, Usuarios

    rol, _ = Roles.objects.get_or_create(
        nombre="FiltroBit", defaults={"es_rol_base": True, "estado": True}
    )
    u = Usuarios.objects.create_user(
        email="filtro.bit@test.local",
        password="x",
        nombre="Filtro",
        apellido="User",
        documento="922222222",
        id_rol=rol,
    )
    Auditoria.objects.create(
        id_usuario=u,
        accion="LOGIN_EXITOSO",
        motivo="—",
        ip="192.168.0.1",
    )
    svc = BitacoraAuditoriaService()
    p = svc.listar(
        {
            "id_usuario": str(u.id_usuario),
            "accion": "LOGIN_EXITOSO",
        }
    )
    assert p.total == 1
    assert p.items[0]["usuario"]["nombre"]


@pytest.mark.unit
@pytest.mark.django_db
def test_excluye_acciones_no_seguridad():
    Auditoria.objects.create(
        id_usuario_id=None,
        accion="EDITAR_USUARIO",
        motivo="—",
        ip="10.0.0.2",
    )
    assert BitacoraAuditoriaService().listar({}).total == 0


@pytest.mark.unit
@pytest.mark.django_db
def test_filtro_id_usuario_invalido():
    svc = BitacoraAuditoriaService()
    with pytest.raises(DominioError) as exc:
        svc.listar({"id_usuario": "nan"})
    assert exc.value.codigo == "FILTRO_INVALIDO"


@pytest.mark.unit
@pytest.mark.django_db
def test_busqueda_libre_y_acciones():
    from apps.m01_identidad.models import Roles, Usuarios

    rol, _ = Roles.objects.get_or_create(
        nombre="QLibre", defaults={"es_rol_base": True, "estado": True}
    )
    u = Usuarios.objects.create_user(
        email="qlibre.bit@test.local",
        password="x",
        nombre="Libre",
        apellido="Busca",
        documento="933333333",
        id_rol=rol,
    )
    Auditoria.objects.create(
        id_usuario=u,
        accion="LOGIN_FALLIDO",
        motivo="Credenciales",
        ip="10.0.0.2",
    )
    svc = BitacoraAuditoriaService()
    assert svc.listar({"q": "Credenciales"}).total == 1
    assert svc.listar({"q": "Libre"}).total == 1
    assert "LOGIN_FALLIDO" in svc.acciones()


@pytest.mark.unit
@pytest.mark.django_db
def test_parse_int_page_bounds():
    svc = BitacoraAuditoriaService()
    pag = svc.listar({"page": "99999", "page_size": "200"})
    assert pag.page_size == 100
    assert pag.page <= 10000
