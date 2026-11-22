from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuarios
from apps.m01_identidad.services import AuthService
from apps.m02_sedes.models import Sedes
from apps.m08_caja.models import Gastos_caja, Reportes_diarios
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter


def _client_admin(sede: Sedes | None = None) -> tuple[APIClient, Sedes]:
    if sede is None:
        sede = Sedes.objects.create(nombre="Sede API Caja", direccion="Calle 1", estado=True, ciudad="BOG")
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    user = Usuarios.objects.create_user(
        email=f"caja11.api.{sede.id_sede}@test.local",
        password="Admin#2026demo",
        nombre="Caja11",
        apellido="API",
        documento=f"10001199{sede.id_sede % 10000:04d}",
        id_rol=rol,
    )
    login = AuthService(audit_port=MagicMock(), email_port=FakeEmailAdapter()).autenticar(
        user.email, "Admin#2026demo", "127.0.0.1", "pytest", "corr-caja11"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.access_token}")
    return client, sede


@pytest.mark.unit
@pytest.mark.django_db
def test_api_epic11_caja_flujo() -> None:
    client, sede = _client_admin()
    assert client.post("/api/v1/caja/categorias/", {}, format="json").status_code == 400
    cat = client.post(
        "/api/v1/caja/categorias/",
        {"nombre": "Operativo", "tipo_movimiento": "Gasto"},
        format="json",
    )
    assert cat.status_code == 201
    id_cat = cat.json()["item"]["id_categoria_movimiento"]
    assert client.get("/api/v1/caja/categorias/?tipo=Gasto").status_code == 200
    assert client.patch(
        f"/api/v1/caja/categorias/{id_cat}/",
        {"nombre": "Operativo", "tipo_movimiento": "Gasto", "version_fila": 1},
        format="json",
    ).status_code == 200
    con = client.post(
        "/api/v1/caja/conceptos/",
        {"nombre": "Agua", "id_categoria": id_cat, "valor_sugerido": "2000"},
        format="json",
    )
    assert con.status_code == 201
    id_con = con.json()["item"]["id_concepto_movimiento"]
    assert client.patch(f"/api/v1/caja/conceptos/{id_con}/", {"nombre": "Agua", "version_fila": 1}, format="json").status_code == 200

    cuenta = client.post(
        "/api/v1/caja/cuentas/",
        {"nombre": "Nequi API", "tipo_cuenta": "Nequi", "numero": "3002223344", "estado": True},
        format="json",
    )
    assert cuenta.status_code in (200, 201)
    id_cuenta = cuenta.json()["item"]["id_cuenta_bancaria"]

    assert client.post("/api/v1/caja/jornada/base-inicial/", {"id_sede": sede.id_sede, "monto": "400000"}, format="json").status_code == 201
    assert client.post("/api/v1/caja/jornada/apertura/", {"id_sede": sede.id_sede}, format="json").status_code == 400
    assert client.get(f"/api/v1/caja/jornada/actual/?id_sede={sede.id_sede}").status_code == 200

    cat_t = client.post(
        "/api/v1/caja/categorias/",
        {"nombre": "Nequi", "tipo_movimiento": "Transferencia"},
        format="json",
    )
    id_cat_t = cat_t.json()["item"]["id_categoria_movimiento"]

    gasto = client.post(
        "/api/v1/caja/movimientos/gastos-ahorros/",
        {
            "id_sede": sede.id_sede,
            "tipo": "gasto",
            "id_categoria": id_cat,
            "valor": "5000",
            "descripcion": "Agua",
        },
        format="json",
    )
    assert gasto.status_code == 201
    assert client.get(f"/api/v1/caja/movimientos/gastos-ahorros/?id_sede={sede.id_sede}").status_code == 200

    trf = client.post(
        "/api/v1/caja/movimientos/transferencias/",
        {
            "id_sede": sede.id_sede,
            "id_categoria": id_cat_t,
            "id_cuenta_bancaria": id_cuenta,
            "valor": "10000",
            "referencia": "REF-API-1",
        },
        format="json",
    )
    assert trf.status_code == 201
    assert client.get(f"/api/v1/caja/movimientos/transferencias/?id_sede={sede.id_sede}").status_code == 200

    assert client.post(
        "/api/v1/caja/adiciones/", {"id_sede": sede.id_sede, "valor": "20000", "motivo": "Base extra"}, format="json"
    ).status_code == 201
    assert client.post(
        "/api/v1/caja/entregas/", {"id_sede": sede.id_sede, "valor": "3000", "descripcion": "Cambio"}, format="json"
    ).status_code == 201
    assert client.post("/api/v1/caja/adjuntos/", {"id_sede": sede.id_sede, "tipo_movimiento": "gasto", "id_movimiento": 1}, format="json").status_code == 200

    cuadre = client.get(f"/api/v1/caja/reporte/cuadre/?id_sede={sede.id_sede}")
    assert cuadre.status_code == 200
    esperado = cuadre.json()["reporte"]["efectivo_esperado"]
    rep = Reportes_diarios.objects.get(id_sede=sede, estado="ABIERTO")
    vf_rep = rep.version_fila
    assert client.patch(
        "/api/v1/caja/reporte/venta-registrada/",
        {"id_sede": sede.id_sede, "venta_registrada": str(esperado), "version_fila": vf_rep},
        format="json",
    ).status_code == 200

    g = Gastos_caja.objects.filter(id_reporte_diario=rep).first()
    assert g is not None
    assert client.post(
        f"/api/v1/caja/movimientos/gasto/{g.id_gasto}/corregir/",
        {"version_fila": 1, "descripcion": "Agua embotellada"},
        format="json",
    ).status_code == 200

    cierre = client.post(
        "/api/v1/caja/reporte/cierre/",
        {
            "id_sede": sede.id_sede,
            "efectivo_declarado": esperado,
            "version_fila": rep.version_fila,
            "base_siguiente": "400000",
        },
        format="json",
    )
    assert cierre.status_code == 200
    vf = cierre.json()["reporte"]["version_fila"]
    assert client.post(
        "/api/v1/caja/reporte/reapertura/",
        {"id_sede": sede.id_sede, "id_reporte_diario": rep.id_reporte_diario, "version_fila": vf},
        format="json",
    ).status_code == 200

    assert client.get(f"/api/v1/caja/historial/?id_sede={sede.id_sede}").status_code == 200
    export_resp = client.get(f"/api/v1/caja/historial/export/?id_sede={sede.id_sede}&formato=csv")
    assert export_resp.status_code == 200
    assert client.get(f"/api/v1/caja/historial/export/?id_sede={sede.id_sede}&formato=xlsx").status_code == 200
    assert client.get(f"/api/v1/caja/historial/?id_sede={sede.id_sede}&desde=2000-01-01&hasta=2099-12-31").status_code == 200
    assert (
        client.post(
            "/api/v1/caja/movimientos/transferencias/",
            {"id_sede": sede.id_sede, "valor": "1"},
            format="json",
        ).status_code
        == 400
    )
