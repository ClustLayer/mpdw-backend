"""Administración de cuentas bancarias (recepción de transferencias POS)."""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.m05_clientes.mensajes import MSG_CONCURRENCIA
from apps.m08_caja import mensajes as msg
from apps.m08_caja.models import TIPOS_CUENTA, Cuentas_bancarias
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

TIPOS_VALIDOS = frozenset(TIPOS_CUENTA)


def _enmascarar_numero(numero: str) -> str:
    n = (numero or "").strip()
    if len(n) <= 4:
        return "****"
    return ("*" * (len(n) - 4)) + n[-4:]


def _serializar(c: Cuentas_bancarias, *, enmascarar: bool = False) -> dict[str, Any]:
    numero = _enmascarar_numero(c.numero) if enmascarar else c.numero
    return {
        "id_cuenta_bancaria": c.id_cuenta_bancaria,
        "nombre": c.nombre,
        "tipo_cuenta": c.tipo_cuenta,
        "banco": c.banco,
        "numero": numero,
        "estado": c.estado,
        "version_fila": c.version_fila,
        "etiqueta": f"{c.nombre} · {c.tipo_cuenta}",
    }


def _auditar(
    ctx: AuthContext,
    accion: str,
    entidad_id: int,
    antes: dict | None,
    despues: dict | None,
    audit: AuditService,
) -> None:
    audit.registrar(
        AuditoriaDTO(
            id_usuario=ctx.id_usuario,
            accion=accion,
            entidad="Cuentas_bancarias",
            id_entidad=entidad_id,
            datos_antes=antes,
            datos_despues=despues,
            motivo=accion,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


class AdminCajaService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def listar_activas(self) -> dict[str, Any]:
        items = [
            _serializar(c) for c in Cuentas_bancarias.objects.filter(estado=True).order_by("nombre")
        ]
        return {"items": items}

    def listar(self, q: str, estado: str | None, page: int, page_size: int) -> dict[str, Any]:
        qs = Cuentas_bancarias.objects.all().order_by("nombre")
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(Q(nombre__icontains=texto) | Q(numero__icontains=texto))
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)
        total = qs.count()
        start = (page - 1) * page_size
        items = [_serializar(c, enmascarar=True) for c in qs[start : start + page_size]]
        return {"items": items, "total": total, "mensaje": msg.MSG_LISTADO.format(n=total)}

    def _validar_body(self, datos: dict[str, Any]) -> tuple[str, str, str]:
        nombre = (datos.get("nombre") or "").strip()
        tipo = (datos.get("tipo_cuenta") or "").strip()
        numero = (datos.get("numero") or "").strip()
        if not nombre or not tipo or not numero:
            raise ReglaNegocioError(msg.MSG_CAMPOS, codigo="VALIDACION")
        if tipo not in TIPOS_VALIDOS:
            raise ReglaNegocioError(msg.MSG_TIPO, codigo="TIPO_INVALIDO")
        return nombre[:150], tipo, numero[:50]

    @transaction.atomic
    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        nombre, tipo, numero = self._validar_body(datos)
        estado = bool(datos.get("estado", True))
        try:
            c = Cuentas_bancarias.objects.create(
                nombre=nombre,
                banco=tipo,
                tipo_cuenta=tipo,
                numero=numero,
                estado=estado,
            )
        except IntegrityError as exc:
            raise ReglaNegocioError(msg.MSG_FALLA, codigo="DUPLICADO") from exc
        ser = _serializar(c)
        _auditar(ctx, "CREAR_CUENTA", c.id_cuenta_bancaria, None, ser, self._audit)
        return {"mensaje": msg.MSG_CREADA, "item": ser}

    @transaction.atomic
    def actualizar(self, ctx: AuthContext, id_cuenta: int, datos: dict[str, Any]) -> dict[str, Any]:
        c = Cuentas_bancarias.objects.select_for_update().filter(pk=id_cuenta).first()
        if not c:
            raise ReglaNegocioError(msg.MSG_FALLA, codigo="NO_ENCONTRADO")
        version = int(datos.get("version_fila") or 0)
        if version != c.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        nombre, tipo, numero = self._validar_body(datos)
        antes = _serializar(c)
        c.nombre = nombre
        c.tipo_cuenta = tipo
        c.banco = tipo
        c.numero = numero
        c.estado = bool(datos.get("estado", c.estado))
        c.version_fila += 1
        c.save()
        despues = _serializar(c)
        _auditar(ctx, "EDITAR_CUENTA", c.id_cuenta_bancaria, antes, despues, self._audit)
        return {"mensaje": msg.MSG_ACTUALIZADA, "item": despues}

    def cuenta_activa(self, id_cuenta: int) -> Cuentas_bancarias:
        c = Cuentas_bancarias.objects.filter(pk=id_cuenta, estado=True).first()
        if not c:
            raise ReglaNegocioError(
                "La cuenta de transferencia no es válida.", codigo="CUENTA_INVALIDA"
            )
        return c
