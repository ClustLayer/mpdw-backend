# ==============================================================================
# Migración Inicial de Identidad, Roles y Sesión - MPDW
# SAD Ref: M01, ADR-004, ADR-006, G-13, G-17
# ==============================================================================
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("m02_sedes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Roles",
            fields=[
                ("id_rol", models.BigAutoField(db_column="id_rol", primary_key=True, serialize=False)),
                ("nombre", models.CharField(db_column="nombre", max_length=50, unique=True)),
                ("descripcion", models.CharField(blank=True, db_column="descripcion", default="", max_length=200)),
                ("es_rol_base", models.BooleanField(db_column="es_rol_base", default=False)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
            ],
            options={
                "db_table": "Roles",
            },
        ),
        migrations.CreateModel(
            name="Permisos",
            fields=[
                ("id_permiso", models.BigAutoField(db_column="id_permiso", primary_key=True, serialize=False)),
                ("modulo", models.CharField(db_column="modulo", max_length=50)),
                ("accion", models.CharField(db_column="accion", max_length=50)),
                ("descripcion", models.CharField(blank=True, db_column="descripcion", default="", max_length=200)),
            ],
            options={
                "db_table": "Permisos",
            },
        ),
        migrations.CreateModel(
            name="Usuarios",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("id_usuario", models.BigAutoField(db_column="id_usuario", primary_key=True, serialize=False)),
                ("email", models.EmailField(db_column="email", max_length=150, unique=True)),
                ("documento", models.CharField(db_column="documento", max_length=20, unique=True)),
                ("nombre", models.CharField(db_column="nombre", max_length=150)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                ("intentos_fallidos", models.IntegerField(db_column="intentos_fallidos", default=0)),
                ("bloqueado_hasta", models.DateTimeField(blank=True, db_column="bloqueado_hasta", null=True)),
                ("dosfa_habilitado", models.BooleanField(db_column="dosfa_habilitado", default=False)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")),
                (
                    "id_rol",
                    models.ForeignKey(
                        db_column="id_rol",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="usuarios",
                        to="m01_identidad.roles",
                    ),
                ),
            ],
            options={
                "db_table": "Usuarios",
            },
        ),
        migrations.CreateModel(
            name="Rol_permiso",
            fields=[
                ("id_rol_permiso", models.BigAutoField(db_column="id_rol_permiso", primary_key=True, serialize=False)),
                (
                    "id_permiso",
                    models.ForeignKey(
                        db_column="id_permiso",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="roles_permiso",
                        to="m01_identidad.permisos",
                    ),
                ),
                (
                    "id_rol",
                    models.ForeignKey(
                        db_column="id_rol",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permisos_rol",
                        to="m01_identidad.roles",
                    ),
                ),
            ],
            options={
                "db_table": "Rol_permiso",
            },
        ),
        migrations.CreateModel(
            name="Usuario_permiso",
            fields=[
                ("id_usuario_permiso", models.BigAutoField(db_column="id_usuario_permiso", primary_key=True, serialize=False)),
                ("permitido", models.BooleanField(db_column="permitido", default=True)),
                (
                    "id_permiso",
                    models.ForeignKey(
                        db_column="id_permiso",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="m01_identidad.permisos",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permisos_usuario",
                        to="m01_identidad.usuarios",
                    ),
                ),
            ],
            options={
                "db_table": "Usuario_permiso",
            },
        ),
        migrations.CreateModel(
            name="Usuario_sede",
            fields=[
                ("id_usuario_sede", models.BigAutoField(db_column="id_usuario_sede", primary_key=True, serialize=False)),
                ("es_principal", models.BooleanField(db_column="es_principal", default=False)),
                ("estado", models.BooleanField(db_column="estado", default=True)),
                (
                    "id_sede",
                    models.ForeignKey(
                        db_column="id_sede",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="m02_sedes.sedes",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sedes_usuario",
                        to="m01_identidad.usuarios",
                    ),
                ),
            ],
            options={
                "db_table": "Usuario_sede",
            },
        ),
        migrations.CreateModel(
            name="Sesiones_usuario",
            fields=[
                ("id_sesion", models.BigAutoField(db_column="id_sesion", primary_key=True, serialize=False)),
                ("refresh_token_hash", models.CharField(db_column="refresh_token_hash", max_length=64, unique=True)),
                ("id_familia", models.UUIDField(db_column="id_familia", default=uuid.uuid4)),
                ("reemplazada_por", models.CharField(blank=True, db_column="reemplazada_por", max_length=64, null=True)),
                ("ultimo_uso", models.DateTimeField(auto_now=True, db_column="ultimo_uso")),
                ("ip_origen", models.GenericIPAddressField(db_column="ip_origen", default="127.0.0.1")),
                ("fecha_expiracion_absoluta", models.DateTimeField(db_column="fecha_expiracion_absoluta")),
                ("revocada", models.BooleanField(db_column="revocada", default=False)),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sesiones",
                        to="m01_identidad.usuarios",
                    ),
                ),
            ],
            options={
                "db_table": "Sesiones_usuario",
            },
        ),
        migrations.AddConstraint(
            model_name="permisos",
            constraint=models.UniqueConstraint(fields=("modulo", "accion"), name="uq_permiso_modulo_accion"),
        ),
        migrations.AddConstraint(
            model_name="rol_permiso",
            constraint=models.UniqueConstraint(fields=("id_rol", "id_permiso"), name="uq_rol_permiso"),
        ),
        migrations.AddConstraint(
            model_name="usuario_permiso",
            constraint=models.UniqueConstraint(fields=("id_usuario", "id_permiso"), name="uq_usuario_permiso"),
        ),
        migrations.AddConstraint(
            model_name="usuario_sede",
            constraint=models.UniqueConstraint(fields=("id_usuario", "id_sede"), name="uq_usuario_sede"),
        ),
        migrations.AddConstraint(
            model_name="usuario_sede",
            constraint=models.UniqueConstraint(
                condition=models.Q(("es_principal", True)),
                fields=("id_usuario",),
                name="uq_usuario_sede_principal",
            ),
        ),
        migrations.AddIndex(
            model_name="sesiones_usuario",
            index=models.Index(fields=["id_familia"], name="idx_sesiones_familia"),
        ),
        migrations.AddIndex(
            model_name="sesiones_usuario",
            index=models.Index(fields=["id_usuario"], name="idx_sesiones_usuario"),
        ),
    ]

