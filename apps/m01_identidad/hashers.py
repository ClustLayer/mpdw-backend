# ==============================================================================
# Hasher de Contraseñas Argon2id - MPDW
# SAD Ref: §10.3, KI-10
# ==============================================================================
from django.contrib.auth.hashers import Argon2PasswordHasher


class Argon2idPasswordHasher(Argon2PasswordHasher):
    """
    Subclase que garantiza parámetros no inferiores a la guía OWASP:
    - time_cost = 2
    - memory_cost = 19456 (19 MiB)
    - parallelism = 1
    """

    time_cost = 2
    memory_cost = 19456
    parallelism = 1
