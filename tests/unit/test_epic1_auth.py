"""Pruebas de HU 03, HU 04 y HU 06 sobre servicios de identidad."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.m01_identidad.mensajes import (
    MSG_2FA_EXPIRADO,
    MSG_2FA_INVALIDO,
    MSG_2FA_OK,
    MSG_CAMBIO_OK,
    MSG_CAMPOS_OBLIGATORIOS,
    MSG_PASSWORD_ACTUAL,
    MSG_PASSWORD_DISTINTA,
    MSG_PASSWORD_POLITICA,
    MSG_RECUPERACION_OK,
    MSG_RESET_INVALIDO,
    MSG_RESET_OK,
)
from apps.m01_identidad.politicas import validar_politica_password
from apps.m01_identidad.repositories import SessionRepository
from apps.m01_identidad.services import (
    AuthService,
    ContrasenaService,
    RecuperacionService,
    Verificacion2FAService,
    emitir_codigo_2fa,
)
from apps.m13_plataforma.adapters.correo_factory import construir_adaptador_correo
from apps.m13_plataforma.adapters.email_smtp import SmtpEmailAdapter
from apps.m13_plataforma.adapters.fakes import FakeEmailAdapter
from apps.m13_plataforma.adapters.plantillas_correo import html_codigo_2fa, html_recuperacion
from contratos.excepciones import AutenticacionError, ReglaNegocioError


def _rol(nombre: str = "Administrador") -> SimpleNamespace:
    return SimpleNamespace(nombre=nombre)


def _usuario(**kwargs: object) -> SimpleNamespace:
    base = {
        "id_usuario": 7,
        "email": "admin@mpdw.test",
        "nombre": "Ana",
        "estado": True,
        "esta_bloqueado": False,
        "dosfa_habilitado": True,
        "debe_cambiar_password": False,
        "id_rol": _rol(),
        "password": "hash",
    }
    base.update(kwargs)
    usuario = SimpleNamespace(**base)

    def check_password(raw: str) -> bool:
        return raw == "Actual#1"

    def set_password(raw: str) -> None:
        usuario.password = f"hash:{raw}"

    usuario.check_password = check_password
    usuario.set_password = set_password
    usuario.save = MagicMock()
    return usuario


@pytest.mark.unit
def test_politica_rechaza_password_debil_y_acepta_fuerte():
    with pytest.raises(ReglaNegocioError, match="requisitos mínimos"):
        validar_politica_password("corta")
    validar_politica_password("ClaveSegura#1")


@pytest.mark.unit
def test_recuperacion_responde_igual_si_el_correo_no_existe():
    users = MagicMock()
    users.buscar_por_email.return_value = None
    email = FakeEmailAdapter()
    servicio = RecuperacionService(user_repo=users, email_port=email)
    assert servicio.solicitar("nadie@mpdw.test") == MSG_RECUPERACION_OK
    assert email.enviados == []


@pytest.mark.unit
def test_recuperacion_envia_enlace_con_fragmento_y_no_guarda_token_en_claro():
    usuario = _usuario(dosfa_habilitado=False)
    users = MagicMock()
    users.buscar_por_email.return_value = usuario
    tokens = MagicMock()
    email = FakeEmailAdapter()
    servicio = RecuperacionService(user_repo=users, token_repo=tokens, email_port=email)
    assert servicio.solicitar(usuario.email) == MSG_RECUPERACION_OK
    tokens.crear.assert_called_once()
    enlace = email.enviados[0]["enlace"]
    assert "#rt=" in enlace
    assert "token=" not in enlace.split("#", 1)[0]


@pytest.mark.unit
def test_restablecer_marca_uso_revoca_sesiones_y_guarda_hash():
    usuario = _usuario()
    registro = SimpleNamespace(
        usado=False,
        expira_en=timezone.now() + timedelta(minutes=30),
        id_usuario=usuario,
    )
    tokens = MagicMock()
    tokens.buscar_por_token.return_value = registro
    sessions = MagicMock()
    servicio = RecuperacionService(token_repo=tokens, session_repo=sessions)
    mensaje = servicio.restablecer("secreto", "NuevaClave#1", "NuevaClave#1")
    assert mensaje == MSG_RESET_OK
    assert usuario.password.startswith("hash:")
    assert usuario.debe_cambiar_password is False
    tokens.marcar_usado.assert_called_once_with(registro)
    sessions.revocar_usuario.assert_called_once_with(usuario.id_usuario)


@pytest.mark.unit
def test_restablecer_token_vencido():
    registro = SimpleNamespace(usado=False, expira_en=timezone.now() - timedelta(minutes=1), id_usuario=_usuario())
    tokens = MagicMock()
    tokens.buscar_por_token.return_value = registro
    servicio = RecuperacionService(token_repo=tokens)
    with pytest.raises(ReglaNegocioError, match=MSG_RESET_INVALIDO):
        servicio.restablecer("x", "NuevaClave#1", "NuevaClave#1")


@pytest.mark.unit
def test_cambio_password_mensajes_de_negocio():
    usuario = _usuario()
    auth = MagicMock()
    auth.emitir_access.return_value = "jwt"
    servicio = ContrasenaService(auth=auth, audit_port=MagicMock())
    with pytest.raises(ReglaNegocioError, match=MSG_CAMPOS_OBLIGATORIOS):
        servicio.cambiar(usuario, "", "NuevaClave#1", "NuevaClave#1", 1, False, "127.0.0.1", "ua", "c")
    with pytest.raises(ReglaNegocioError, match=MSG_PASSWORD_ACTUAL):
        servicio.cambiar(usuario, "mala", "NuevaClave#1", "NuevaClave#1", 1, False, "127.0.0.1", "ua", "c")
    with pytest.raises(ReglaNegocioError, match=MSG_PASSWORD_DISTINTA):
        servicio.cambiar(usuario, "Actual#1", "NuevaClave#1", "OtraClave#1", 1, False, "127.0.0.1", "ua", "c")
    with pytest.raises(ReglaNegocioError, match=MSG_PASSWORD_POLITICA):
        servicio.cambiar(usuario, "Actual#1", "Actual#1", "Actual#1", 1, False, "127.0.0.1", "ua", "c")


@pytest.mark.unit
def test_cambio_password_exitoso_no_audita_el_secreto():
    usuario = _usuario(debe_cambiar_password=True)
    auth = MagicMock()
    auth.emitir_access.return_value = "jwt-nuevo"
    audit = MagicMock()
    servicio = ContrasenaService(auth=auth, audit_port=audit)
    acceso, mensaje, sigue = servicio.cambiar(
        usuario, "Actual#1", "NuevaClave#1", "NuevaClave#1", 4, False, "10.0.0.8", "ua", "corr"
    )
    assert acceso == "jwt-nuevo"
    assert mensaje == MSG_CAMBIO_OK
    assert sigue is False
    evento = audit.registrar.call_args.args[0]
    assert evento.datos_despues["password"] == "[omitido]"
    assert "NuevaClave#1" not in str(evento.datos_despues)


@pytest.mark.unit
def test_login_administrador_2fa_no_emite_sesion_ni_registra_el_codigo():
    usuario = _usuario()
    users = MagicMock()
    users.buscar_por_email.return_value = usuario
    users.obtener_sedes_asignadas_ids.return_value = ()
    sessions = MagicMock()
    codigos = MagicMock()
    email = FakeEmailAdapter()
    auth = AuthService(user_repo=users, session_repo=sessions, email_port=email, codigo_repo=codigos)
    resultado = auth.autenticar(usuario.email, "Actual#1")
    assert resultado.requiere_2fa is True
    assert resultado.access_token is None
    assert resultado.refresh_token is None
    assert resultado.desafio_token
    sessions.registrar_sesion.assert_not_called()
    assert email.enviados[0]["codigo"] not in (resultado.desafio_token or "")
    codigos.crear.assert_called_once()


@pytest.mark.unit
def test_2fa_codigo_invalido_expirado_y_exitoso():
    usuario = _usuario(dosfa_habilitado=True)
    users = MagicMock()
    users.buscar_por_id.return_value = usuario
    users.obtener_sedes_asignadas_ids.return_value = ()
    codigo = "123456"
    registro = SimpleNamespace(
        usado=False,
        expira_en=timezone.now() + timedelta(minutes=5),
        codigo_hash=SessionRepository.calcular_hash(codigo),
        intentos=0,
    )
    codigos = MagicMock()
    codigos.buscar_vigente.return_value = registro
    codigos.registrar_fallo.return_value = 1
    sessions = MagicMock()
    sessions.registrar_sesion.return_value = SimpleNamespace(id_sesion=3, mfa_verificada=True)
    auth = AuthService(user_repo=users, session_repo=sessions, codigo_repo=codigos)
    servicio = Verificacion2FAService(auth=auth, codigo_repo=codigos, session_repo=sessions)
    desafio = auth.emitir_desafio(usuario)
    with pytest.raises(ReglaNegocioError, match=MSG_2FA_INVALIDO):
        servicio.verificar(None, desafio, "000000", None, "127.0.0.1", "ua", "c")

    registro.usado = True
    with pytest.raises(ReglaNegocioError, match=MSG_2FA_EXPIRADO):
        servicio.verificar(None, desafio, codigo, None, "127.0.0.1", "ua", "c")

    registro.usado = False
    registro.expira_en = datetime.now(UTC) + timedelta(minutes=5)
    resultado = servicio.verificar(None, desafio, codigo, None, "127.0.0.1", "ua", "c")
    assert resultado.mensaje == MSG_2FA_OK
    assert resultado.access_token
    assert resultado.refresh_token
    codigos.marcar_usado.assert_called_once()


@pytest.mark.unit
@pytest.mark.unit
def test_plantillas_y_smtp_no_filtran_configuracion(monkeypatch):
    html = html_recuperacion("https://app.local/nueva-contrasena#rt=abc")
    codigo = html_codigo_2fa("654321")
    assert "Restablecer contraseña" in html
    assert "654321" in codigo
    enviados: list[object] = []

    class FalsoSMTP:
        def __init__(self, host: str, port: int, timeout: int = 15) -> None:
            enviados.append((host, port))

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            assert password == "no-se-registra"

        def send_message(self, mensaje: object) -> None:
            enviados.append(mensaje)

    monkeypatch.setattr("apps.m13_plataforma.adapters.email_smtp.smtplib.SMTP", FalsoSMTP)
    adapter = SmtpEmailAdapter(host="smtp.local", port=587, user="user", password="no-se-registra", use_tls=True)
    assert adapter.enviar_codigo_2fa("persona@mpdw.test", "654321") is True
    assert enviados

    monkeypatch.setattr("apps.m13_plataforma.adapters.correo_factory.settings.SENDGRID_API_KEY", "")
    monkeypatch.setattr("apps.m13_plataforma.adapters.correo_factory.settings.SMTP_HOST", "smtp.local")
    assert isinstance(construir_adaptador_correo(), SmtpEmailAdapter)


@pytest.mark.unit
def test_emitir_codigo_falla_si_el_correo_no_sale():
    email = MagicMock()
    email.enviar_codigo_2fa.return_value = False
    with pytest.raises(AutenticacionError):
        emitir_codigo_2fa(MagicMock(), email, _usuario(), "No fue posible iniciar sesión. Intente nuevamente.")
