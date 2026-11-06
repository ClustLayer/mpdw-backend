"""Unit tests — equivalencias permiso_eval."""

import pytest

from apps.m01_identidad.permiso_eval import ACCIONES_CATALOGO, candidatas_para


@pytest.mark.unit
def test_acciones_catalogo_incluye_sin_acceso_y_total():
    assert "Sin acceso" in ACCIONES_CATALOGO
    assert "Total" in ACCIONES_CATALOGO


@pytest.mark.unit
def test_candidatas_total_y_desconocida():
    assert "Total" in candidatas_para("Crear")
    assert candidatas_para("Custom") == ("Custom",)
