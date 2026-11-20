import pytest

from apps.m01_identidad.models import Roles, Usuarios
from apps.m08_caja.admin_caja_service import AdminCajaService
from apps.m08_caja.models import Cuentas_bancarias
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError


@pytest.fixture
def ctx() -> AuthContext:
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email="caja@test.local",
        password="Admin#2026demo",
        nombre="Caja",
        apellido="Test",
        documento="100009990501",
        id_rol=rol,
    )
    return AuthContext(user.id_usuario, user.email, "Administrador", (), True, id_rol=rol.id_rol, ip="127.0.0.1")


@pytest.mark.unit
@pytest.mark.django_db
def test_crear_cuenta(ctx: AuthContext) -> None:
    r = AdminCajaService().crear(
        ctx,
        {"nombre": "Test Nequi", "tipo_cuenta": "Nequi", "numero": "3009998877", "estado": True},
    )
    assert "creada" in r["mensaje"]
    assert Cuentas_bancarias.objects.filter(nombre="Test Nequi").exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_tipo_invalido(ctx: AuthContext) -> None:
    with pytest.raises(ReglaNegocioError):
        AdminCajaService().crear(ctx, {"nombre": "X", "tipo_cuenta": "Otro", "numero": "1"})
