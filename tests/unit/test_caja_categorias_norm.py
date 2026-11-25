"""Normalización de tipos de categoría de caja."""

from __future__ import annotations

import pytest

from apps.m01_identidad.models import Roles, Usuarios
from apps.m08_caja.caja_epic11_service import CajaEpic11Service, _norm_tipo_categoria
from contratos.dtos import AuthContext

pytestmark = pytest.mark.unit


@pytest.mark.django_db
def test_norm_tipo_categoria_acepta_minusculas():
    assert _norm_tipo_categoria("gasto") == "Gasto"
    assert _norm_tipo_categoria("Transferencia") == "Transferencia"
    assert _norm_tipo_categoria("AHORRO") == "Ahorro"
    assert _norm_tipo_categoria("adicion") == ""


@pytest.mark.django_db
def test_crear_categoria_con_tipo_minuscula(db):
    rol, _ = Roles.objects.get_or_create(
        nombre="Administrador", defaults={"es_rol_base": True, "estado": True}
    )
    user = Usuarios.objects.create_user(
        email="cat.caja@test.local",
        password="Admin#2026demo",
        nombre="Cat",
        apellido="Caja",
        documento="200200200",
        id_rol=rol,
    )
    ctx = AuthContext(user.id_usuario, user.email, "Administrador", (), True, id_rol=rol.id_rol)
    data = CajaEpic11Service().crear_categoria(
        ctx, {"nombre": "Papelería", "tipo_movimiento": "gasto", "descripcion": "x"}
    )
    assert data["item"]["tipo_movimiento"] == "Gasto"
    listed = CajaEpic11Service().listar_categorias("gasto", "")
    assert any(i["nombre"] == "Papelería" for i in listed["items"])
