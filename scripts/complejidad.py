"""Complejidad ciclomatica aproximada. Falla solo en funciones nuevas de identidad por encima de 20."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBJETIVO = ROOT / "apps" / "m01_identidad" / "services.py"
LIMITE = 20


def complejidad(nodo: ast.AST) -> int:
    total = 1
    for hijo in ast.walk(nodo):
        if isinstance(hijo, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.Assert)):
            total += 1
        elif isinstance(hijo, ast.BoolOp):
            total += max(len(hijo.values) - 1, 0)
    return total


def main() -> int:
    arbol = ast.parse(OBJETIVO.read_text(encoding="utf-8"))
    exceso = False
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef):
            valor = complejidad(nodo)
            print(f"{nodo.name}: {valor}")
            if valor > LIMITE:
                exceso = True
        if isinstance(nodo, ast.ClassDef):
            for hijo in nodo.body:
                if isinstance(hijo, ast.FunctionDef):
                    valor = complejidad(hijo)
                    print(f"{nodo.name}.{hijo.name}: {valor}")
                    if valor > LIMITE:
                        exceso = True
    if exceso:
        print(f"Hay funciones sobre el limite {LIMITE}.")
        return 1
    print(f"Complejidad dentro del limite {LIMITE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
