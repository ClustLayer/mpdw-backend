# ==============================================================================
# Prueba de Contrato: Integridad de la Especificación OpenAPI 3.0
# SAD Ref: §6.6, §9.1, §14.2
# ==============================================================================
import difflib
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command


@pytest.mark.unit
def test_contrato_openapi_debe_coincidir_exactamente_con_el_artefacto_publicado():
    """
    Verifica que la especificación OpenAPI generada dinámicamente desde el código
    coincida byte a byte con 'docs/openapi.yaml', evitando deriva arquitectónica.
    """
    openapi_file = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.yaml"
    assert openapi_file.exists(), f"El archivo de contrato {openapi_file} no existe"

    contenido_existente = openapi_file.read_text(encoding="utf-8")

    out = StringIO()
    call_command("spectacular", stdout=out, validate=True)
    contenido_generado = out.getvalue()

    if contenido_existente.strip() != contenido_generado.strip():
        diff = difflib.unified_diff(
            contenido_existente.splitlines(),
            contenido_generado.splitlines(),
            fromfile="docs/openapi.yaml",
            tofile="spectacular_generado",
            lineterm="",
        )
        diff_text = "\n".join(diff)
        pytest.fail(f"El contrato docs/openapi.yaml difiere de la especificación generada:\n{diff_text}")
