"""POS debe reutilizar jornada ABIERTO aunque la fecha no sea hoy (RI-10)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.m01_identidad.models import Roles, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m06_ventas.admin_ventas_service import AdminVentasService
from apps.m08_caja.models import Reportes_diarios
from contratos.dtos import AuthContext

pytestmark = pytest.mark.unit


@pytest.fixture
def sede_y_usuario(db):
    rol, _ = Roles.objects.get_or_create(
        nombre="Administrador", defaults={"es_rol_base": True, "estado": True}
    )
    user = Usuarios.objects.create_user(
        email="jornada.pos@test.local",
        password="Test#12345",
        nombre="Jornada",
        apellido="POS",
        documento="99001122",
        id_rol=rol,
    )
    sede = Sedes.objects.create(nombre="Sede Jornada", direccion="Calle 1", ciudad="Cali", estado=True)
    return sede, user


@pytest.mark.django_db
def test_asegurar_jornada_reutiliza_abierto_fecha_anterior(sede_y_usuario):
    sede, user = sede_y_usuario
    ayer = timezone.localdate() - timedelta(days=5)
    Reportes_diarios.objects.create(
        id_sede_id=sede.id_sede,
        fecha=ayer,
        base_inicial=Decimal("0"),
        estado="ABIERTO",
        id_usuario_apertura_id=user.id_usuario,
    )
    ctx = AuthContext(
        id_usuario=user.id_usuario,
        email=user.email,
        rol_nombre="Administrador",
        sedes_asignadas=(sede.id_sede,),
        es_global=True,
    )
    svc = AdminVentasService()
    svc._asegurar_jornada(ctx, sede.id_sede)
    assert Reportes_diarios.objects.filter(id_sede_id=sede.id_sede, estado="ABIERTO").count() == 1
    assert Reportes_diarios.objects.get(id_sede_id=sede.id_sede, estado="ABIERTO").fecha == ayer


@pytest.mark.django_db
def test_jornada_abierta_sin_filtrar_fecha(sede_y_usuario):
    sede, user = sede_y_usuario
    Reportes_diarios.objects.create(
        id_sede_id=sede.id_sede,
        fecha=date(2020, 1, 1),
        base_inicial=Decimal("0"),
        estado="ABIERTO",
        id_usuario_apertura_id=user.id_usuario,
    )
    svc = AdminVentasService()
    assert svc._jornada_abierta(sede.id_sede) is True
