from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m02_sedes.models import Sedes
from apps.m11_eventos.admin_eventos_service import AdminEventosService
from apps.m11_eventos.models import IMPACTO_MEDIO, TIPO_PROMOCION, Eventos_novedades
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    return AuthContext(0, "a@test.local", "Administrador", (1,), True, id_rol=1, ip="127.0.0.1")


@pytest.mark.unit
@pytest.mark.django_db
def test_evento_crud(ctx):
    sede = Sedes.objects.create(nombre="Sede Eventos", direccion="Calle 1", estado=True)
    svc = AdminEventosService(audit=MagicMock())
    inicio = timezone.now()
    body = {
        "tipo": TIPO_PROMOCION,
        "titulo": "Promo pinturas",
        "descripcion": "Descuento de temporada",
        "fecha_inicio": inicio.isoformat(),
        "impacto": IMPACTO_MEDIO,
        "id_sede": sede.id_sede,
        "visible_sitio": True,
    }
    out = svc.crear(ctx, body)
    assert "correctamente" in out["mensaje"]
    pk = out["evento"]["id_evento"]
    fin = inicio
    patch = svc.actualizar(
        ctx,
        pk,
        {
            **body,
            "titulo": "Promo actualizada",
            "fecha_fin": fin.isoformat(),
            "version_fila": 1,
            "estado": True,
        },
    )
    assert patch["evento"]["titulo"] == "Promo actualizada"
    pub = svc.publicos()
    assert pub["items"]


@pytest.mark.unit
@pytest.mark.django_db
def test_evento_fechas_invalidas(ctx):
    svc = AdminEventosService(audit=MagicMock())
    inicio = timezone.now()
    fin = inicio - timezone.timedelta(days=1)
    with pytest.raises(ReglaNegocioError) as exc:
        svc.crear(
            ctx,
            {
                "tipo": "demo_especial",
                "titulo": "T",
                "descripcion": "D",
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": fin.isoformat(),
            },
        )
    assert exc.value.codigo == "FECHAS_INVALIDAS"
    with pytest.raises(ReglaNegocioError):
        svc.crear(ctx, {"tipo": TIPO_PROMOCION, "titulo": "", "descripcion": "x", "fecha_inicio": inicio.isoformat()})


@pytest.mark.unit
@pytest.mark.django_db
def test_api_eventos():
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="ev.admin@test.local",
        password="Admin#2026demo",
        nombre="Ev",
        apellido="Admin",
        documento="100009990166",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-ev"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    assert client.get("/api/v1/eventos/").status_code == 200
    assert client.get("/api/v1/eventos/publicos/").status_code == 200
    assert client.get("/api/v1/eventos/sedes-activas/").status_code == 200
    r = client.post(
        "/api/v1/eventos/",
        {
            "tipo": TIPO_PROMOCION,
            "titulo": "API Evento",
            "descripcion": "Desde test",
            "fecha_inicio": timezone.now().isoformat(),
        },
        format="json",
    )
    assert r.status_code == 201
    pk = r.json()["evento"]["id_evento"]
    assert client.get(f"/api/v1/eventos/{pk}/").status_code == 200
    assert client.patch(
        f"/api/v1/eventos/{pk}/",
        {
            "tipo": TIPO_PROMOCION,
            "titulo": "API actualizado",
            "descripcion": "Desde test",
            "fecha_inicio": timezone.now().isoformat(),
            "version_fila": 1,
        },
        format="json",
    ).status_code == 200
    assert client.get("/api/v1/eventos/9999999/").status_code == 404


@pytest.mark.unit
@pytest.mark.django_db
def test_evento_concurrencia(ctx):
    svc = AdminEventosService(audit=MagicMock())
    out = svc.crear(
        ctx,
        {
            "tipo": TIPO_PROMOCION,
            "titulo": "X",
            "descripcion": "Y",
            "fecha_inicio": timezone.now().isoformat(),
        },
    )
    pk = out["evento"]["id_evento"]
    with pytest.raises(ReglaNegocioError) as exc:
        svc.actualizar(
            ctx,
            pk,
            {
                "tipo": TIPO_PROMOCION,
                "titulo": "Z",
                "descripcion": "W",
                "fecha_inicio": timezone.now().isoformat(),
                "version_fila": 99,
            },
        )
    assert exc.value.codigo == "CONCURRENCIA"


@pytest.mark.unit
@pytest.mark.django_db
def test_evento_sin_coincidencias(ctx):
    assert AdminEventosService().listar("nohayevento123", "todos", 1, 10)["mensaje"]
    assert AdminEventosService().sedes_activas()["items"] is not None


@pytest.mark.unit
@pytest.mark.django_db
def test_evento_listado_y_impacto(ctx):
    svc = AdminEventosService(audit=MagicMock())
    svc.crear(
        ctx,
        {
            "tipo": TIPO_PROMOCION,
            "titulo": "L",
            "descripcion": "D",
            "fecha_inicio": timezone.now().isoformat(),
        },
    )
    assert svc.listar("", "activo", 1, 10)["items"]
    with pytest.raises(ReglaNegocioError):
        svc.crear(
            ctx,
            {
                "tipo": TIPO_PROMOCION,
                "titulo": "X",
                "descripcion": "Y",
                "fecha_inicio": timezone.now().isoformat(),
                "impacto": "Crítico",
            },
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_evento_tipo_demo(ctx):
    svc = AdminEventosService(audit=MagicMock())
    out = svc.crear(
        ctx,
        {
            "tipo": "social",
            "titulo": "Feria barrio",
            "descripcion": "Actividad comunitaria",
            "fecha_inicio": timezone.now().isoformat(),
        },
    )
    assert out["evento"]["tipo"] == "social"
    assert Eventos_novedades.objects.filter(pk=out["evento"]["id_evento"]).exists()
