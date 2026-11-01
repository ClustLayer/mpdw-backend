# ==============================================================================
# Pruebas Unitarias de Hasher Argon2id - MPDW
# SAD Ref: §10.3, KI-10
# ==============================================================================
import pytest

from apps.m01_identidad.hashers import Argon2idPasswordHasher


@pytest.mark.unit
def test_argon2id_hasher_parametros_minimos_seguridad_owasp():
    hasher = Argon2idPasswordHasher()
    # Memoria >= 19 MiB (19456 KiB)
    assert hasher.memory_cost >= 19456, f"memory_cost insuficiente: {hasher.memory_cost}"
    # Tiempo >= 2
    assert hasher.time_cost >= 2, f"time_cost insuficiente: {hasher.time_cost}"
    # Paralelismo >= 1
    assert hasher.parallelism >= 1, f"parallelism insuficiente: {hasher.parallelism}"
