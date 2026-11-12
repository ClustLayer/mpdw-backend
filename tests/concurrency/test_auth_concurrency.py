# ==============================================================================
# Pruebas de concurrencia en flujos de autenticacion (PostgreSQL)
# ==============================================================================
import threading

import pytest
from django.utils import timezone

from apps.m01_identidad.models import Codigos_2fa, Roles, Tokens_recuperacion, Usuarios
from apps.m01_identidad.repositories import Codigo2FARepository, RecuperacionRepository
from apps.m01_identidad.services import emitir_codigo_2fa


@pytest.mark.django_db(transaction=True)
@pytest.mark.concurrency
def test_recuperacion_solo_un_consumo_atomico():
    rol, _ = Roles.objects.get_or_create(nombre="Empleado", defaults={"es_rol_base": True, "estado": True})
    usuario = Usuarios.objects.create_user(
        email="conc.recovery@mpdw.test",
        password="Anterior123!",
        nombre="Conc Recovery",
        documento="8800000001",
        id_rol=rol,
    )
    repo = RecuperacionRepository()
    token = "token-concurrencia-recuperacion"
    repo.crear(usuario, token, 30)
    resultados: list[bool] = []

    def intentar() -> None:
        reg = repo.consumir_token_atomico(token)
        resultados.append(reg is not None)

    hilos = [threading.Thread(target=intentar) for _ in range(4)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert resultados.count(True) == 1
    assert Tokens_recuperacion.objects.filter(id_usuario=usuario, usado=True).count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.concurrency
def test_2fa_serializa_emision_de_codigos():
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True, "estado": True})
    usuario = Usuarios.objects.create_user(
        email="conc.2fa@mpdw.test",
        password="Admin123456!",
        nombre="Conc 2FA",
        documento="8800000002",
        id_rol=rol,
        dosfa_habilitado=True,
    )
    codigos = Codigo2FARepository()
    email = type("E", (), {"enviar_codigo_2fa": lambda _s, _d, _c: True})()

    def emitir() -> None:
        emitir_codigo_2fa(codigos, email, usuario, "fallo")

    hilos = [threading.Thread(target=emitir) for _ in range(5)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    vigentes = Codigos_2fa.objects.filter(id_usuario=usuario, usado=False, expira_en__gte=timezone.now())
    assert vigentes.count() == 1
