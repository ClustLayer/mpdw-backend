# ==============================================================================
# Pruebas Unitarias de la Matriz de Autorización (Anexo A SAD §18) - MPDW
# SAD Ref: §4.1, §18 Anexo A, BR-10, QA-05.
# Cubre exhaustivamente las 57 celdas contractuales (19 secciones × 3 roles base).
# ==============================================================================
import pytest

from apps.m01_identidad.services import PermissionService
from contratos.catalogos import MATRIZ_ANEXO_A
from contratos.dtos import AuthContext


class FakePermissionRepoAnexoA:
    """Emulador de repositorio de permisos cargado desde la fuente única MATRIZ_ANEXO_A."""

    def __init__(self) -> None:
        self.permisos_por_rol: dict[str, set[tuple[str, str]]] = {
            "Empleado": set(),
            "Gerente": set(),
            "Administrador": set(),
        }
        for _, modulo, _, emp_acc, ger_acc, adm_acc in MATRIZ_ANEXO_A:
            if emp_acc != "—":
                self.permisos_por_rol["Empleado"].add((modulo, emp_acc))
            if ger_acc != "—":
                self.permisos_por_rol["Gerente"].add((modulo, ger_acc))
            if adm_acc != "—":
                self.permisos_por_rol["Administrador"].add((modulo, adm_acc))

    def tiene_permiso(self, id_usuario: int, id_rol: int, modulo: str, accion: str) -> bool:
        rol_nombre = {1: "Administrador", 2: "Gerente", 3: "Empleado"}.get(id_rol, "")
        return (modulo, accion) in self.permisos_por_rol.get(rol_nombre, set())


# Generar las 57 celdas contractuales (19 secciones × 3 roles base)
CASOS_57_CELDAS = []
for id_sec, modulo, nombre_sec, emp_acc, ger_acc, adm_acc in MATRIZ_ANEXO_A:
    CASOS_57_CELDAS.append((f"{id_sec}. {nombre_sec}", modulo, "Empleado", 3, emp_acc))
    CASOS_57_CELDAS.append((f"{id_sec}. {nombre_sec}", modulo, "Gerente", 2, ger_acc))
    CASOS_57_CELDAS.append((f"{id_sec}. {nombre_sec}", modulo, "Administrador", 1, adm_acc))


@pytest.mark.unit
@pytest.mark.parametrize("seccion,modulo,rol_nombre,id_rol,nivel_esperado", CASOS_57_CELDAS)
def test_qa_05_matriz_autorizacion_57_celdas_anexo_a(seccion, modulo, rol_nombre, id_rol, nivel_esperado):
    """
    SAD §18 Anexo A & QA-05:
    Valida contractualmente cada celda de la matriz de permisos para los roles base:
      - 'T' (Total/CRUD): Permiso total concedido.
      - 'L' (Lectura/consulta): Permiso de lectura concedido.
      - 'O' (Operación transaccional): Permiso de operación transaccional concedido.
      - '—' (Sin acceso): Todo acceso denegado.
    """
    repo = FakePermissionRepoAnexoA()
    service = PermissionService(repo=repo)

    ctx = AuthContext(
        id_usuario=100,
        email=f"user_{rol_nombre.lower()}@mpdw.com",
        rol_nombre=rol_nombre,
        sedes_asignadas=(1,),
        es_global=False,
        id_rol=id_rol,
    )

    if nivel_esperado in ("T", "L", "O"):
        # La acción específica debe estar autorizada
        assert service.tiene_permiso(ctx, modulo=modulo, accion=nivel_esperado) is True, (
            f"Fallo en {seccion}: {rol_nombre} deberia tener accion '{nivel_esperado}'"
        )
    elif nivel_esperado == "—":
        # Ninguna acción debe estar autorizada para este módulo
        for accion in ("T", "L", "O", "crear", "editar", "eliminar"):
            assert service.tiene_permiso(ctx, modulo=modulo, accion=accion) is False, (
                f"Fallo en {seccion}: {rol_nombre} tiene acceso prohibido ('—') pero se permitio '{accion}'"
            )
