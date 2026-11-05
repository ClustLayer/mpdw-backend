# ==============================================================================
# Pruebas Unitarias de AuthService y Rotación con Detección de Reúso - MPDW
# SAD Ref: M01, ADR-006, §10.3, QA-06, QA-07, TC-A09
# ==============================================================================
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from apps.m01_identidad.services import AuthService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import AutenticacionError


class FakeUser:
    def __init__(
        self,
        id_usuario: int = 1,
        email: str = "test@mundopinturasdiana.com",
        password: str = "correct_password",
        estado: bool = True,
        bloqueado: bool = False,
        rol_nombre: str = "Vendedor",
    ) -> None:
        self.id_usuario = id_usuario
        self.email = email
        self._password = password
        self.estado = estado
        self._bloqueado = bloqueado
        self.id_rol = MagicMock()
        self.id_rol.nombre = rol_nombre

    @property
    def esta_bloqueado(self) -> bool:
        return self._bloqueado

    def check_password(self, raw_password: str) -> bool:
        return self._password == raw_password


class FakeSession:
    def __init__(
        self,
        id_sesion: int = 10,
        id_usuario: FakeUser | None = None,
        id_familia: uuid.UUID | None = None,
        revocada: bool = False,
        reemplazada_por: str | None = None,
        expiracion_absoluta: datetime | None = None,
        ultimo_uso: datetime | None = None,
    ) -> None:
        self.id_sesion = id_sesion
        self.id_usuario = id_usuario or FakeUser()
        self.id_usuario_id = self.id_usuario.id_usuario
        self.id_familia = id_familia or uuid.uuid4()
        self.revocada = revocada
        self.reemplazada_por = reemplazada_por
        ahora = datetime.now(UTC)
        self.fecha_expiracion_absoluta = expiracion_absoluta or (ahora + timedelta(days=7))
        self.ultimo_uso = ultimo_uso or ahora


class FakeAuditPort:
    def __init__(self) -> None:
        self.eventos: list[AuditoriaDTO] = []

    def registrar(self, dto: AuditoriaDTO) -> None:
        self.eventos.append(dto)


@pytest.mark.unit
def test_login_exitoso_emite_tokens_y_auditoria():
    user_repo = MagicMock()
    session_repo = MagicMock()
    audit_port = FakeAuditPort()

    usuario = FakeUser(id_usuario=1, email="admin@diana.com", rol_nombre="Administrador")
    user_repo.buscar_por_email.return_value = usuario
    user_repo.obtener_sedes_asignadas_ids.return_value = (1, 2)

    fake_session = FakeSession(id_sesion=42, id_usuario=usuario)
    session_repo.registrar_sesion.return_value = fake_session

    auth_service = AuthService(user_repo=user_repo, session_repo=session_repo, audit_port=audit_port)

    resultado = auth_service.autenticar(
        email="admin@diana.com",
        password="correct_password",
        ip="192.168.1.10",
        user_agent="Mozilla/5.0",
        id_correlacion="corr-123",
    )

    assert resultado.access_token is not None
    assert resultado.refresh_token is not None
    assert isinstance(resultado.ctx, AuthContext)
    assert resultado.ctx is not None
    assert resultado.ctx.id_usuario == 1
    assert resultado.ctx.email == "admin@diana.com"
    assert resultado.ctx.rol_nombre == "Administrador"
    assert resultado.ctx.es_global is True
    assert resultado.ctx.sedes_asignadas == (1, 2)
    assert resultado.mensaje == "Bienvenido(a), admin@diana.com."
    user_repo.registrar_acceso_exitoso.assert_called_once_with(usuario)
    assert len(audit_port.eventos) == 1
    assert audit_port.eventos[0].accion == "LOGIN_EXITOSO"


@pytest.mark.unit
def test_login_fallo_credenciales_invalidas_incrementa_intentos():
    user_repo = MagicMock()
    usuario = FakeUser(id_usuario=2, email="user@diana.com")
    user_repo.buscar_por_email.return_value = usuario

    auth_service = AuthService(user_repo=user_repo)

    with pytest.raises(AutenticacionError, match="Credenciales no válidas"):
        auth_service.autenticar(email="user@diana.com", password="wrong_password")

    user_repo.incrementar_intentos_fallidos.assert_called_once()


@pytest.mark.unit
def test_login_fallo_usuario_bloqueado():
    user_repo = MagicMock()
    usuario = FakeUser(id_usuario=3, email="locked@diana.com", bloqueado=True)
    user_repo.buscar_por_email.return_value = usuario

    auth_service = AuthService(user_repo=user_repo)

    with pytest.raises(AutenticacionError, match="Acceso temporalmente bloqueado"):
        auth_service.autenticar(email="locked@diana.com", password="correct_password")

    user_repo.incrementar_intentos_fallidos.assert_not_called()


@pytest.mark.unit
def test_login_fallo_usuario_inactivo():
    user_repo = MagicMock()
    usuario = FakeUser(id_usuario=4, email="inactive@diana.com", estado=False)
    user_repo.buscar_por_email.return_value = usuario

    auth_service = AuthService(user_repo=user_repo)

    with pytest.raises(AutenticacionError, match="Credenciales no válidas"):
        auth_service.autenticar(email="inactive@diana.com", password="correct_password")

    user_repo.incrementar_intentos_fallidos.assert_not_called()


@pytest.mark.unit
def test_rotacion_refresh_token_exitosa():
    session_repo = MagicMock()
    usuario = FakeUser(id_usuario=5)
    sesion = FakeSession(id_sesion=100, id_usuario=usuario)
    session_repo.buscar_por_token.return_value = sesion

    nueva_sesion = FakeSession(id_sesion=101, id_usuario=usuario)
    session_repo.rotar_sesion.return_value = nueva_sesion

    auth_service = AuthService(session_repo=session_repo)

    nuevo_access, nuevo_refresh = auth_service.rotar_refresh_token("valid_token")

    assert nuevo_access is not None
    assert nuevo_refresh is not None
    session_repo.rotar_sesion.assert_called_once()


@pytest.mark.unit
def test_rotacion_refresh_token_detecta_reuso_y_revoca_familia(monkeypatch):
    """SAD TC-A09 / ADR-006: Reúso de refresh token revoca la familia completa."""
    session_repo = MagicMock()
    audit_port = FakeAuditPort()
    usuario = FakeUser(id_usuario=6)
    familia_id = uuid.uuid4()

    # Sesión ya reemplazada
    sesion_reusada = FakeSession(
        id_sesion=200,
        id_usuario=usuario,
        id_familia=familia_id,
        reemplazada_por="hash_del_sucesor",
    )
    session_repo.buscar_por_token.return_value = sesion_reusada

    auth_service = AuthService(session_repo=session_repo, audit_port=audit_port)

    with pytest.raises(AutenticacionError, match="expirado"):
        auth_service.rotar_refresh_token("token_reutilizado")

    session_repo.revocar_familia.assert_called_once_with(familia_id)
    assert len(audit_port.eventos) == 1
    assert audit_port.eventos[0].accion == "ALERTA_REUSO_TOKEN"


@pytest.mark.unit
def test_rotacion_refresh_token_expiracion_absoluta():
    session_repo = MagicMock()
    usuario = FakeUser(id_usuario=7)
    sesion_expirada = FakeSession(
        id_sesion=300,
        id_usuario=usuario,
        expiracion_absoluta=datetime.now(UTC) - timedelta(days=1),
    )
    session_repo.buscar_por_token.return_value = sesion_expirada

    auth_service = AuthService(session_repo=session_repo)

    with pytest.raises(AutenticacionError, match="expirado"):
        auth_service.rotar_refresh_token("token_expirado")


@pytest.mark.unit
def test_rotacion_refresh_token_inactividad():
    session_repo = MagicMock()
    usuario = FakeUser(id_usuario=8)
    sesion_inactiva = FakeSession(
        id_sesion=400,
        id_usuario=usuario,
        ultimo_uso=datetime.now(UTC) - timedelta(minutes=90),
    )
    session_repo.buscar_por_token.return_value = sesion_inactiva

    auth_service = AuthService(session_repo=session_repo)

    with pytest.raises(AutenticacionError, match="inactividad"):
        auth_service.rotar_refresh_token("token_inactivo")


@pytest.mark.unit
def test_rotacion_token_no_existente():
    session_repo = MagicMock()
    session_repo.buscar_por_token.return_value = None

    auth_service = AuthService(session_repo=session_repo)

    with pytest.raises(AutenticacionError, match="expirado"):
        auth_service.rotar_refresh_token("token_fantasma")


@pytest.mark.unit
def test_cerrar_sesion_revoca_familia():
    session_repo = MagicMock()
    familia_id = uuid.uuid4()
    sesion = FakeSession(id_sesion=500, id_familia=familia_id, revocada=False)
    session_repo.buscar_por_token.return_value = sesion

    auth_service = AuthService(session_repo=session_repo)
    auth_service.cerrar_sesion("token_a_cerrar")

    session_repo.revocar_familia.assert_called_once_with(familia_id)


@pytest.mark.unit
def test_qa_06_bloqueo_cuenta_tras_5_intentos_fallidos():
    """
    Escenario QA-06: 5 intentos fallidos consecutivos bloquean temporalmente la cuenta (15 min)
    y disparan el evento de auditoría de seguridad.
    """
    user_repo = MagicMock()
    audit_port = FakeAuditPort()
    usuario = FakeUser(id_usuario=99, email="cajero_bloqueo@mpdw.com", password="real_password")

    def simular_incremento(u, max_intentos=5, minutos_bloqueo=15):
        u._bloqueado = True
        return True

    user_repo.buscar_por_email.return_value = usuario
    user_repo.incrementar_intentos_fallidos.side_effect = simular_incremento

    auth_service = AuthService(user_repo=user_repo, audit_port=audit_port)

    with pytest.raises(AutenticacionError, match="Acceso temporalmente bloqueado"):
        auth_service.autenticar(email="cajero_bloqueo@mpdw.com", password="wrong")

    user_repo.incrementar_intentos_fallidos.assert_called_once()
    assert usuario.esta_bloqueado is True
    assert len(audit_port.eventos) == 1
    assert audit_port.eventos[0].accion == "BLOQUEO_POR_INTENTOS"
    assert "password" not in (audit_port.eventos[0].datos_despues or {})

    with pytest.raises(AutenticacionError, match="Acceso temporalmente bloqueado"):
        auth_service.autenticar(email="cajero_bloqueo@mpdw.com", password="real_password")

    user_repo.incrementar_intentos_fallidos.assert_called_once()

