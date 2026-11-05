"""Falla si un archivo versionado parece contener un secreto. No lee .env local."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xsmtpsib-[0-9a-f]{20,}"),
    re.compile(r"SG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}"),
]
BINARIOS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".woff", ".woff2"}


def archivos_versionados() -> list[Path]:
    resultado = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    nombres = [parte for parte in resultado.stdout.decode("utf-8").split("\0") if parte]
    return [ROOT / nombre for nombre in nombres]


def main() -> int:
    hallazgos: list[str] = []
    for path in archivos_versionados():
        nombre = path.name
        if nombre == ".env":
            hallazgos.append(f"archivo de entorno versionado: {path.relative_to(ROOT)}")
            continue
        if nombre.startswith(".env.") and not nombre.endswith(".example"):
            hallazgos.append(f"archivo de entorno versionado: {path.relative_to(ROOT)}")
            continue
        if path.suffix.lower() in BINARIOS or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                hallazgos.append(f"{path.relative_to(ROOT)} coincide con un patron de secreto")
                break
    if hallazgos:
        print("Se detectaron posibles secretos:")
        for item in hallazgos:
            print(f" - {item}")
        return 1
    print("Escaneo de secretos: sin hallazgos en archivos versionados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
