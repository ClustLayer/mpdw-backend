import pytest
from django.core.management import call_command

from apps.m01_identidad.services import PermissionService
from apps.m03_catalogo.models import Categorias_producto, Marcas, Tipos_producto
from contratos.dtos import AuthContext


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
        id_correlacion="ep5-ctx",
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_seed_catalogo_parametros_idempotente():
    call_command("seed_catalogo_parametros")
    assert Tipos_producto.objects.filter(es_base=True).count() >= 5
    assert Categorias_producto.objects.filter(nombre="Vinilos").exists()
    assert Marcas.objects.filter(nombre="Diana").exists()
    call_command("seed_catalogo_parametros")
    assert Tipos_producto.objects.filter(nombre="Producto Terminado", es_base=True).count() == 1


@pytest.mark.unit
@pytest.mark.django_db
def test_accesos_panel_replica_catalogo_en_pantallas(ctx_admin):
    data = PermissionService().accesos_panel(ctx_admin)
    for clave in ("productos", "categorias", "marcas", "tipos_producto"):
        assert clave in data["modulos"]
    assert data["acciones_por_modulo"]["marcas"] == data["acciones_por_modulo"]["productos"]
