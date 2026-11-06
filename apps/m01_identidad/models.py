# ==============================================================================
# Modelos de Identidad, Acceso y Sesión - MPDW
# SAD Ref: M01, ADR-004, ADR-006, ADR-007, §8.1, G-13, G-17, RI-01, RI-21, RI-24, RI-25
# ==============================================================================
import uuid
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager["Usuarios"]):
    """Manager para creación y consulta de Usuarios mediante email."""

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "Usuarios":
        if not email:
            raise ValueError("El correo electronico es obligatorio.")
        email = self.normalize_email(email)
        user: Usuarios = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user


class Roles(models.Model):
    """Catálogo de roles del sistema (SAD §8.1, BR-10)."""

    id_rol = models.BigAutoField(primary_key=True, db_column="id_rol")
    nombre = models.CharField(max_length=50, unique=True, db_column="nombre")  # G-17
    descripcion = models.CharField(max_length=200, blank=True, default="", db_column="descripcion")
    es_rol_base = models.BooleanField(default=False, db_column="es_rol_base")  # RI-21
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Roles"

    def __str__(self) -> str:
        return self.nombre


class Permisos(models.Model):
    """Permisos granulares por módulo y acción (SAD §8.1, BR-10)."""

    id_permiso = models.BigAutoField(primary_key=True, db_column="id_permiso")
    modulo = models.CharField(max_length=50, db_column="modulo")
    accion = models.CharField(max_length=50, db_column="accion")
    descripcion = models.CharField(max_length=200, blank=True, default="", db_column="descripcion")

    class Meta:
        db_table = "Permisos"
        constraints = [
            models.UniqueConstraint(fields=["modulo", "accion"], name="uq_permiso_modulo_accion"),  # G-17
        ]

    def __str__(self) -> str:
        return f"{self.modulo}:{self.accion}"


class Rol_permiso(models.Model):
    """Asignación de permisos a roles (SAD §8.1)."""

    id_rol_permiso = models.BigAutoField(primary_key=True, db_column="id_rol_permiso")
    id_rol = models.ForeignKey(Roles, on_delete=models.CASCADE, db_column="id_rol", related_name="permisos_rol")
    id_permiso = models.ForeignKey(Permisos, on_delete=models.CASCADE, db_column="id_permiso", related_name="roles_permiso")

    class Meta:
        db_table = "Rol_permiso"
        constraints = [
            models.UniqueConstraint(fields=["id_rol", "id_permiso"], name="uq_rol_permiso"),  # G-17
        ]


class Usuarios(AbstractBaseUser):
    """Entidad principal de usuarios del sistema (SAD §8.1, BR-08, BR-09)."""

    id_usuario = models.BigAutoField(primary_key=True, db_column="id_usuario")
    email = models.EmailField(max_length=255, unique=True, db_column="email")  # RI-01, HU 01 CA 2.1
    documento = models.CharField(max_length=20, unique=True, db_column="documento")  # RI-01
    nombre = models.CharField(max_length=255, db_column="nombre")
    apellido = models.CharField(max_length=255, blank=True, default="", db_column="apellido")
    telefono = models.CharField(max_length=20, blank=True, default="", db_column="telefono")
    tipo_sangre = models.CharField(max_length=5, blank=True, default="", db_column="tipo_sangre")
    fecha_nacimiento = models.DateField(null=True, blank=True, db_column="fecha_nacimiento")
    direccion = models.CharField(max_length=255, blank=True, default="", db_column="direccion")
    contacto_emergencia_nombre = models.CharField(
        max_length=255, blank=True, default="", db_column="contacto_emergencia_nombre"
    )
    contacto_emergencia_telefono = models.CharField(
        max_length=20, blank=True, default="", db_column="contacto_emergencia_telefono"
    )
    id_rol = models.ForeignKey(Roles, on_delete=models.PROTECT, db_column="id_rol", related_name="usuarios")
    estado = models.BooleanField(default=True, db_column="estado")  # RI-24
    intentos_fallidos = models.IntegerField(default=0, db_column="intentos_fallidos")
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, db_column="bloqueado_hasta")
    dosfa_habilitado = models.BooleanField(default=False, db_column="dosfa_habilitado")  # G-13
    debe_cambiar_password = models.BooleanField(default=False, db_column="debe_cambiar_password")
    credential_version = models.PositiveIntegerField(default=1, db_column="credential_version")
    contrasena_temporal_expira = models.DateTimeField(null=True, blank=True, db_column="contrasena_temporal_expira")
    version_fila = models.PositiveIntegerField(default=1, db_column="version_fila")
    ultimo_acceso = models.DateTimeField(null=True, blank=True, db_column="ultimo_acceso")
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True, blank=True, db_column="fecha_actualizacion")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre", "documento"]

    class Meta:
        db_table = "Usuarios"

    @property
    def esta_bloqueado(self) -> bool:
        if self.bloqueado_hasta and self.bloqueado_hasta > timezone.now():
            return True
        return False

    @property
    def password_hash(self) -> str:
        """Hash almacenado por Django. Nunca es la contraseña en claro."""
        return self.password

    def __str__(self) -> str:
        return f"{self.email} ({self.id_rol.nombre})"


class Usuario_permiso(models.Model):
    """Excepciones de permiso individuales por usuario (SAD §8.1, BR-10)."""

    id_usuario_permiso = models.BigAutoField(primary_key=True, db_column="id_usuario_permiso")
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column="id_usuario", related_name="permisos_usuario")
    id_permiso = models.ForeignKey(Permisos, on_delete=models.CASCADE, db_column="id_permiso")
    permitido = models.BooleanField(default=True, db_column="permitido")  # True = override otorga, False = override deniega

    class Meta:
        db_table = "Usuario_permiso"
        constraints = [
            models.UniqueConstraint(fields=["id_usuario", "id_permiso"], name="uq_usuario_permiso"),  # G-17
        ]


class Usuario_sede(models.Model):
    """Alcance territorial de usuarios por sede (SAD §8.1, RI-25, ADR-007)."""

    id_usuario_sede = models.BigAutoField(primary_key=True, db_column="id_usuario_sede")
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column="id_usuario", related_name="sedes_usuario")
    id_sede = models.ForeignKey("m02_sedes.Sedes", on_delete=models.CASCADE, db_column="id_sede")
    es_principal = models.BooleanField(default=False, db_column="es_principal")
    estado = models.BooleanField(default=True, db_column="estado")

    class Meta:
        db_table = "Usuario_sede"
        constraints = [
            models.UniqueConstraint(fields=["id_usuario", "id_sede"], name="uq_usuario_sede"),  # G-17
            models.UniqueConstraint(
                fields=["id_usuario"],
                condition=models.Q(es_principal=True),
                name="uq_usuario_sede_principal",  # RI-25
            ),
        ]


class Sesiones_usuario(models.Model):
    """Sesiones activas y rotación de refresh tokens con seguimiento de familias (ADR-006, G-13)."""

    id_sesion = models.BigAutoField(primary_key=True, db_column="id_sesion")
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column="id_usuario", related_name="sesiones")
    refresh_token_hash = models.CharField(max_length=64, unique=True, db_column="refresh_token_hash")  # IX-7
    id_familia = models.UUIDField(default=uuid.uuid4, db_column="id_familia")  # G-13
    reemplazada_por = models.CharField(max_length=64, null=True, blank=True, db_column="reemplazada_por")  # G-13
    ultimo_uso = models.DateTimeField(auto_now=True, db_column="ultimo_uso")
    ip_origen = models.GenericIPAddressField(default="127.0.0.1", db_column="ip_origen")
    fecha_expiracion_absoluta = models.DateTimeField(db_column="fecha_expiracion_absoluta")  # G-13
    fecha_revocacion = models.DateTimeField(null=True, blank=True, db_column="fecha_revocacion")
    mfa_verificada = models.BooleanField(default=True, db_column="mfa_verificada")
    revocada = models.BooleanField(default=False, db_column="revocada")

    class Meta:
        db_table = "Sesiones_usuario"
        indexes = [
            models.Index(fields=["id_familia"], name="idx_sesiones_familia"),
            models.Index(fields=["id_usuario"], name="idx_sesiones_usuario"),
        ]

    @property
    def fecha_expiracion(self):
        """Nombre de dominio de HU 01. La columna física sigue siendo fecha_expiracion_absoluta."""
        return self.fecha_expiracion_absoluta


class Tokens_recuperacion(models.Model):
    """Tokens de un solo uso para recuperación de contraseña (SAD §10.3)."""

    id_token = models.BigAutoField(primary_key=True, db_column="id_token")
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column="id_usuario")
    token_hash = models.CharField(max_length=64, unique=True, db_column="token_hash")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, db_column="fecha_creacion")
    expira_en = models.DateTimeField(db_column="expira_en")
    usado = models.BooleanField(default=False, db_column="usado")

    class Meta:
        db_table = "Tokens_recuperacion"

    @property
    def fecha_expiracion(self):
        return self.expira_en


class Codigos_2fa(models.Model):
    """Códigos de verificación para segundo factor de autenticación (SAD §10.3)."""

    id_codigo = models.BigAutoField(primary_key=True, db_column="id_codigo")
    id_usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column="id_usuario")
    codigo_hash = models.CharField(max_length=64, db_column="codigo_hash")
    intentos = models.IntegerField(default=0, db_column="intentos")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, db_column="fecha_creacion")
    expira_en = models.DateTimeField(db_column="expira_en")
    usado = models.BooleanField(default=False, db_column="usado")

    class Meta:
        db_table = "Codigos_2fa"

    @property
    def fecha_expiracion(self):
        return self.expira_en

