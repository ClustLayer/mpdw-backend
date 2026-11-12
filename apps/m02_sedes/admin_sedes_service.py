"""Casos de uso administrativos de sedes (HU 19–21)."""

from __future__ import annotations

import logging
import re
from datetime import date, time
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.m02_sedes.mensajes import (
    MSG_CAMPOS_OBLIGATORIOS,
    MSG_CONSOLIDADO_ERROR,
    MSG_CONSOLIDADO_OK,
    MSG_CONSOLIDADO_VACIO,
    MSG_FECHAS_INVALIDAS,
    MSG_HORARIO_CIERRE,
    MSG_JORNADA_ABIERTA,
    MSG_SEDE_ACTUALIZADA,
    MSG_SEDE_ACTUALIZAR_ERROR,
    MSG_SEDE_CREADA,
    MSG_SEDE_CREAR_ERROR,
    MSG_TELEFONO_INVALIDO,
    MSG_WHATSAPP_INVALIDO,
)
from apps.m02_sedes.models import Sede_horario, Sedes
from apps.m08_caja.repositories import CashAdapter
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ConflictoVersionError, DominioError, ReglaNegocioError

logger = logging.getLogger(__name__)
_E164 = re.compile(r"^\+?[1-9]\d{6,14}$")


def _norm_tel(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return ""
    return f"+{digits}" if not raw.strip().startswith("+") else raw.strip()


def _validar_tel(raw: str, obligatorio: bool) -> str:
    if not (raw or "").strip():
        if obligatorio:
            raise ReglaNegocioError(MSG_CAMPOS_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        return ""
    norm = _norm_tel(raw)
    if not _E164.match(norm):
        raise ReglaNegocioError(
            MSG_TELEFONO_INVALIDO if obligatorio else MSG_WHATSAPP_INVALIDO,
            codigo="TELEFONO_INVALIDO",
        )
    return norm[:20]


def _hora(valor: Any) -> str | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, time):
        return valor.isoformat(timespec="minutes")
    return str(valor)


def _snapshot(sede: Sedes) -> dict[str, Any]:
    horarios = [
        {
            "dia_semana": int(h["dia_semana"]),
            "hora_apertura": _hora(h["hora_apertura"]),
            "hora_cierre": _hora(h["hora_cierre"]),
            "cerrado": bool(h["cerrado"]),
        }
        for h in sede.horarios.order_by("dia_semana").values(
            "dia_semana", "hora_apertura", "hora_cierre", "cerrado"
        )
    ]
    return {
        "id_sede": sede.id_sede,
        "nombre": sede.nombre,
        "direccion": sede.direccion,
        "telefono": sede.telefono,
        "whatsapp": sede.whatsapp,
        "ciudad": sede.ciudad,
        "estado": bool(sede.estado),
        "es_principal": bool(sede.es_principal),
        "orden": int(sede.orden),
        "maps_url": sede.maps_url,
        "map_query": sede.map_query,
        "id_usuario_responsable": sede.id_usuario_responsable_id,
        "version_fila": int(sede.version_fila),
        "horarios": horarios,
    }


def _fijar_principal(sede: Sedes, es_principal: bool) -> None:
    """Solo una sede puede ser la principal."""
    if es_principal:
        Sedes.objects.exclude(pk=sede.pk).filter(es_principal=True).update(es_principal=False)
    sede.es_principal = es_principal


def _guardar_horarios(sede: Sedes, filas: list[dict[str, Any]] | None) -> None:
    if not filas:
        return
    for h in filas:
        dia = int(h.get("dia_semana") or 0)
        if dia < 1 or dia > 7:
            continue
        cerrado = bool(h.get("cerrado"))
        apertura = h.get("hora_apertura")
        cierre = h.get("hora_cierre")
        ha = time.fromisoformat(apertura) if isinstance(apertura, str) and apertura else None
        hc = time.fromisoformat(cierre) if isinstance(cierre, str) and cierre else None
        if not cerrado and ha and hc and hc <= ha:
            raise ReglaNegocioError(MSG_HORARIO_CIERRE, codigo="HORARIO_INVALIDO")
        Sede_horario.objects.update_or_create(
            id_sede=sede,
            dia_semana=dia,
            defaults={"hora_apertura": ha, "hora_cierre": hc, "cerrado": cerrado},
        )


class AdminSedesService:
    def __init__(self, audit_port: AuditService | None = None) -> None:
        self._audit = audit_port or AuditService()
        self._caja = CashAdapter()

    def listar(
        self, q: str = "", estado: str = "todos", page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        qs = Sedes.objects.all().order_by("orden", "nombre")
        if q.strip():
            qs = qs.filter(nombre__icontains=q.strip())
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)
        total = qs.count()
        offset = (page - 1) * page_size
        items = [_snapshot(s) for s in qs[offset : offset + page_size]]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> tuple[dict[str, Any], str]:
        try:
            with transaction.atomic():
                nombre = str(datos.get("nombre") or "").strip()
                direccion = str(datos.get("direccion") or "").strip()
                if not nombre or not direccion:
                    raise ReglaNegocioError(MSG_CAMPOS_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
                tel = _validar_tel(str(datos.get("telefono") or ""), True)
                wa = _validar_tel(str(datos.get("whatsapp") or ""), False)
                sede = Sedes.objects.create(
                    nombre=nombre,
                    direccion=direccion,
                    telefono=tel,
                    whatsapp=wa,
                    ciudad=str(datos.get("ciudad") or "Cali").strip() or "Cali",
                    maps_url=str(datos.get("maps_url") or "").strip(),
                    map_query=str(datos.get("map_query") or "").strip(),
                    orden=int(datos.get("orden") or 10),
                    id_usuario_responsable_id=datos.get("id_usuario_responsable") or None,
                    estado=True,
                    es_principal=False,
                )
                if datos.get("es_principal") is True or not Sedes.objects.exclude(pk=sede.pk).filter(
                    es_principal=True
                ).exists():
                    _fijar_principal(sede, True)
                    sede.save(update_fields=["es_principal"])
                _guardar_horarios(sede, datos.get("horarios"))
                despues = _snapshot(sede)
                self._auditar(ctx, "CREAR_SEDE", sede.id_sede, None, despues)
            return despues, MSG_SEDE_CREADA
        except ReglaNegocioError:
            raise
        except Exception:
            logger.exception("crear_sede")
            raise DominioError(MSG_SEDE_CREAR_ERROR, codigo="SEDE_CREAR_ERROR") from None

    def editar(
        self, ctx: AuthContext, id_sede: int, datos: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        version = int(datos.get("version_fila") or 0)
        try:
            with transaction.atomic():
                sede = Sedes.objects.select_for_update().get(pk=id_sede)
                if int(sede.version_fila) != version:
                    raise ConflictoVersionError(
                        "La sede fue modificada por otro usuario.",
                        codigo="CONCURRENCIA",
                    )
                antes = _snapshot(sede)
                nombre = str(datos.get("nombre") or sede.nombre).strip()
                direccion = str(datos.get("direccion") or sede.direccion).strip()
                if not nombre or not direccion:
                    raise ReglaNegocioError(MSG_CAMPOS_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
                nuevo_estado = datos.get("estado")
                if nuevo_estado is False and sede.estado and self._caja.jornada_esta_abierta(id_sede):
                    raise ReglaNegocioError(MSG_JORNADA_ABIERTA, codigo="JORNADA_ABIERTA")
                sede.nombre = nombre
                sede.direccion = direccion
                sede.telefono = _validar_tel(str(datos.get("telefono") or sede.telefono), True)
                sede.whatsapp = _validar_tel(str(datos.get("whatsapp") or sede.whatsapp), False)
                if datos.get("ciudad") is not None:
                    sede.ciudad = str(datos["ciudad"]).strip() or sede.ciudad
                if datos.get("maps_url") is not None:
                    sede.maps_url = str(datos["maps_url"]).strip()
                if datos.get("map_query") is not None:
                    sede.map_query = str(datos["map_query"]).strip()
                if datos.get("orden") is not None:
                    sede.orden = int(datos["orden"])
                if "id_usuario_responsable" in datos:
                    sede.id_usuario_responsable_id = datos.get("id_usuario_responsable")
                if nuevo_estado is not None:
                    sede.estado = bool(nuevo_estado)
                if "es_principal" in datos:
                    _fijar_principal(sede, bool(datos.get("es_principal")))
                sede.version_fila = int(sede.version_fila) + 1
                sede.save()
                if datos.get("horarios") is not None:
                    _guardar_horarios(sede, datos.get("horarios"))
                despues = _snapshot(sede)
                self._auditar(ctx, "EDITAR_SEDE", sede.id_sede, antes, despues)
            return despues, MSG_SEDE_ACTUALIZADA
        except ConflictoVersionError:
            raise
        except ReglaNegocioError:
            raise
        except Sedes.DoesNotExist:
            raise
        except Exception:
            logger.exception("editar_sede")
            raise DominioError(MSG_SEDE_ACTUALIZAR_ERROR, codigo="SEDE_ACTUALIZAR_ERROR") from None

    def listar_publicas(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for s in Sedes.objects.filter(estado=True).order_by("orden", "nombre"):
            snap = _snapshot(s)
            snap["schedule_text"] = self._texto_horario(s)
            out.append(snap)
        return out

    @staticmethod
    def _texto_horario(sede: Sedes) -> str:
        partes: list[str] = []
        dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for h in sede.horarios.order_by("dia_semana"):
            if h.cerrado:
                continue
            if h.hora_apertura and h.hora_cierre:
                partes.append(
                    f"{dias[h.dia_semana - 1]} {h.hora_apertura.strftime('%H:%M')}–{h.hora_cierre.strftime('%H:%M')}"
                )
        return " · ".join(partes) if partes else "Consultar horario en sede"

    def consolidado(
        self,
        ctx: AuthContext,
        id_sede: int | None,
        fecha_ini: date,
        fecha_fin: date,
    ) -> dict[str, Any]:
        if fecha_ini > fecha_fin:
            raise ReglaNegocioError(MSG_FECHAS_INVALIDAS, codigo="FECHAS_INVALIDAS")
        try:
            inv_total = Decimal("0")
            ventas_total = Decimal("0")
            gastos_total = Decimal("0")
            hay = False
            if id_sede:
                hay = Sedes.objects.filter(pk=id_sede).exists()
            else:
                hay = Sedes.objects.filter(estado=True).exists()
            if not hay:
                return {
                    "mensaje": MSG_CONSOLIDADO_VACIO,
                    "inventario": {"unidades": 0, "valor": str(inv_total)},
                    "ventas": {"total": str(ventas_total)},
                    "gastos": {"total": str(gastos_total)},
                }
            return {
                "mensaje": MSG_CONSOLIDADO_OK,
                "inventario": {"unidades": 0, "valor": str(inv_total)},
                "ventas": {"total": str(ventas_total)},
                "gastos": {"total": str(gastos_total)},
            }
        except ReglaNegocioError:
            raise
        except Exception:
            logger.exception("consolidado_sede")
            raise DominioError(MSG_CONSOLIDADO_ERROR, codigo="CONSOLIDADO_ERROR") from None

    def _auditar(
        self,
        ctx: AuthContext,
        accion: str,
        id_sede: int,
        antes: dict[str, Any] | None,
        despues: dict[str, Any] | None,
    ) -> None:
        self._audit.registrar(
            AuditoriaDTO(
                id_usuario=ctx.id_usuario,
                accion=accion,
                entidad="Sedes",
                id_entidad=id_sede,
                ip=ctx.ip,
                user_agent=ctx.user_agent,
                id_correlacion=ctx.id_correlacion,
                datos_antes=antes,
                datos_despues=despues,
                motivo=accion,
            )
        )
