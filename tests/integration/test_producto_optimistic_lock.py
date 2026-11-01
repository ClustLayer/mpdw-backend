# ==============================================================================
# Prueba de Integración: Control de Concurrencia Optimista (HTTP 409) - MPDW
# SAD Ref: M03, ADR-005, NF-08, TC-A12, QA-11
# ==============================================================================
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.m01_identidad.models import Roles, Usuario_sede, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Categorias_producto, Productos


@pytest.mark.django_db
@pytest.mark.integration
def test_debe_retornar_409_conflicto_cuando_version_esta_desactualizada():
    # Arrange
    client = APIClient()

    sede, _ = Sedes.objects.get_or_create(nombre="Sede Norte", defaults={"direccion": "Calle 100"})
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True})
    user = Usuarios.objects.create_user(email="admin_opt@mpdw.com", password="Password123!", nombre="Admin", documento="123", id_rol=rol)
    Usuario_sede.objects.create(id_usuario=user, id_sede=sede, es_principal=True)

    cat = Categorias_producto.objects.first() or Categorias_producto.objects.create(nombre="Esmaltes")
    producto = Productos.objects.create(
        codigo_producto="ESM-01",
        nombre="Esmalte Sintetico",
        precio_venta=Decimal("15000.00"),
        id_categoria=cat,
        version=1,
    )

    client.force_authenticate(user=user)

    # Act 1: Primer usuario actualiza precio con version 1 -> Exito (v1 -> v2)
    res1 = client.patch(
        f"/api/v1/products/{producto.id_producto}/price",
        data={"nuevo_precio": "16500.00", "motivo": "Aumento de costos", "version": 1},
        format="json",
    )
    assert res1.status_code == status.HTTP_200_OK
    assert res1.data["version"] == 2
    assert res1.data["precio_venta"] == "16500.00"

    # Act 2: Segundo usuario intenta actualizar enviando la version antigua v1 -> HTTP 409 Conflict
    res2 = client.patch(
        f"/api/v1/products/{producto.id_producto}/price",
        data={"nuevo_precio": "17000.00", "motivo": "Actualizacion simultanea", "version": 1},
        format="json",
    )

    # Assert
    assert res2.status_code == status.HTTP_409_CONFLICT
    assert res2.data["codigo"] == "CONFLICTO_CONCURRENCIA"
    assert "conflicto" in res2.data["mensaje"].lower()
    assert "idCorrelacion" in res2.data

