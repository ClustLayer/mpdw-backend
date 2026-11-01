# ==============================================================================
# Prueba de Integración: Formato Uniforme de Errores JSON - MPDW
# SAD Ref: §9.1
# ==============================================================================
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.integration
def test_debe_retornar_cuerpo_uniforme_ante_recurso_no_encontrado():
    client = APIClient()
    response = client.get("/api/v1/products/99999999/price")

    # Requiere autenticación -> 401
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.data
    assert "codigo" in data
    assert "mensaje" in data
    assert "detalles" in data
    assert "idCorrelacion" in data
    assert data["codigo"] == "NO_AUTENTICADO"

