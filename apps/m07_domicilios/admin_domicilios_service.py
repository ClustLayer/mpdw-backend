"""Backoffice domicilios, mensajeros e historial (HU 52–58)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.m01_identidad.models import Usuarios
from apps.m05_clientes.mensajes import MSG_CONCURRENCIA
from apps.m05_clientes.models import Clientes
from apps.m06_ventas.models import Facturas
from apps.m07_domicilios import mensajes as msg
from apps.m07_domicilios.domicilios_logica import (
    ESTADOS_ETIQUETA,
    anos_trabajados,
    antiguedad_desde,
    duracion_entrega,
    transicion_permitida,
    transiciones_desde,
)
from apps.m07_domicilios.models import Entregas, Historial_entregas, Mensajeros
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

TELEFONO_RE = re.compile(r"^[+0-9A-Za-z\- ()]{0,20}$")
ESTADOS_BANDEJA = ("PENDIENTE", "ASIGNADO", "EN_CAMINO")


def _usuario_id(ctx: AuthContext) -> int | None:
    if not ctx.id_usuario:
        return None
    if not Usuarios.objects.filter(pk=ctx.id_usuario).exists():
        return None
    return ctx.id_usuario


def _auditar(
    ctx: AuthContext,
    accion: str,
    entidad: str,
    entidad_id: int,
    antes: dict | None,
    despues: dict | None,
    audit: AuditService,
) -> None:
    audit.registrar(
        AuditoriaDTO(
            id_usuario=_usuario_id(ctx),
            accion=accion,
            entidad=entidad,
            id_entidad=entidad_id,
            datos_antes=antes,
            datos_despues=despues,
            motivo=accion,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


def _decimal(val: Any, campo: str) -> Decimal:
    try:
        d = Decimal(str(val))
    except (InvalidOperation, TypeError) as exc:
        raise ReglaNegocioError(msg.MSG_CAMPOS_OBLIGATORIOS, codigo="VALIDACION") from exc
    if d < 0:
        raise ReglaNegocioError(msg.MSG_VALOR_NEGATIVO, codigo="VALIDACION")
    return d


def _telefono_opcional(val: str | None) -> str:
    t = (val or "").strip()
    if not t:
        return ""
    if len(t) > 20 or not TELEFONO_RE.match(t):
        raise ReglaNegocioError(msg.MSG_TELEFONO, codigo="FORMATO_TELEFONO")
    return t


def _es_factura_domicilio(factura: Facturas) -> bool:
    return (factura.id_tipo_venta.nombre or "").strip().lower() == "domicilio"


def _consecutivo_factura(f: Facturas) -> str:
    return f"{f.serie}-{f.numero_factura}"


def _nombre_cliente(factura: Facturas) -> str:
    c = factura.id_cliente
    if not c:
        return factura.comprador_nombre or "Sin cliente"
    return f"{c.nombre} {c.apellido}".strip()


def _serializar_mensajero(m: Mensajeros) -> dict[str, Any]:
    return {
        "id_mensajero": m.id_mensajero,
        "nombre": m.nombre,
        "apellido": m.apellido,
        "nombre_completo": f"{m.nombre} {m.apellido}".strip(),
        "documento": m.documento,
        "telefono": m.telefono,
        "fecha_inicio": m.fecha_inicio.isoformat(),
        "tarifa_promedio": str(m.tarifa_promedio),
        "observaciones": m.observaciones,
        "estado": m.estado,
        "version_fila": m.version_fila,
        "anos_trabajados": anos_trabajados(m.fecha_inicio),
    }


def _serializar_entrega(e: Entregas, *, incluir_historial: bool = False) -> dict[str, Any]:
    factura = e.id_factura
    cliente = factura.id_cliente
    ant = antiguedad_desde(e.fecha_solicitud)
    mensajero = e.id_mensajero
    data: dict[str, Any] = {
        "id_entrega": e.id_entrega,
        "id_factura": factura.id_factura,
        "consecutivo_factura": _consecutivo_factura(factura),
        "cliente": _nombre_cliente(factura),
        "direccion": e.direccion,
        "telefono_contacto": e.telefono_contacto,
        "estado": e.estado,
        "estado_etiqueta": ESTADOS_ETIQUETA.get(e.estado, e.estado),
        "id_mensajero": mensajero.id_mensajero if mensajero else None,
        "mensajero": _serializar_mensajero(mensajero)["nombre_completo"] if mensajero else "",
        "fecha_solicitud": e.fecha_solicitud.isoformat(),
        "fecha_asignacion": e.fecha_asignacion.isoformat() if e.fecha_asignacion else None,
        "fecha_salida": e.fecha_salida.isoformat() if e.fecha_salida else None,
        "fecha_entrega": e.fecha_entrega.isoformat() if e.fecha_entrega else None,
        "valor_cobrado_cliente": str(e.valor_cobrado_cliente),
        "valor_pagado_mensajero": str(e.valor_pagado_mensajero),
        "observaciones": e.observaciones,
        "version_fila": e.version_fila,
        "id_sede": factura.id_sede_id,
        "antiguedad": ant,
        "duracion": duracion_entrega(e),
        "transiciones_permitidas": transiciones_desde(e.estado),
    }
    if cliente:
        data["id_cliente"] = cliente.id_cliente
    if incluir_historial:
        data["historial"] = [
            {
                "estado_anterior": h.estado_anterior,
                "estado_nuevo": h.estado_nuevo,
                "fecha_hora": h.fecha_hora.isoformat(),
                "observaciones": h.observaciones,
                "id_usuario": h.id_usuario_id,
            }
            for h in e.historial.select_related("id_usuario").all()
        ]
    return data


class AdminDomiciliosService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def precarga_factura(self, id_factura: int) -> dict[str, Any]:
        factura = Facturas.objects.select_related("id_cliente", "id_tipo_venta").filter(pk=id_factura).first()
        if not factura:
            raise ReglaNegocioError(msg.MSG_FACTURA_INVALIDA, codigo="NO_ENCONTRADO")
        if not _es_factura_domicilio(factura):
            raise ReglaNegocioError(msg.MSG_FACTURA_INVALIDA, codigo="FACTURA_NO_DOMICILIO")
        if Entregas.objects.filter(id_factura=factura, estado__in=ESTADOS_BANDEJA).exists():
            raise ReglaNegocioError(msg.MSG_FACTURA_INVALIDA, codigo="ENTREGA_ACTIVA")
        c: Clientes | None = factura.id_cliente
        return {
            "id_factura": factura.id_factura,
            "consecutivo_factura": _consecutivo_factura(factura),
            "direccion": (c.direccion if c else "") or "",
            "telefono_contacto": (c.numero_telefono if c else factura.comprador_telefono) or "",
        }

    @transaction.atomic
    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        id_factura = int(datos.get("id_factura") or 0)
        direccion = (datos.get("direccion") or "").strip()
        if not direccion:
            raise ReglaNegocioError(msg.MSG_DIRECCION, codigo="VALIDACION")
        if len(direccion) > 255:
            raise ReglaNegocioError(msg.MSG_DIRECCION, codigo="VALIDACION")
        telefono = _telefono_opcional(str(datos.get("telefono_contacto") or ""))
        valor_cli = _decimal(datos.get("valor_cobrado_cliente"), "valor_cobrado_cliente")
        valor_msg = _decimal(datos.get("valor_pagado_mensajero"), "valor_pagado_mensajero")
        observaciones = (datos.get("observaciones") or "").strip()[:500]
        id_mensajero = int(datos.get("id_mensajero") or 0)
        mensajero: Mensajeros | None = None
        if id_mensajero:
            mensajero = Mensajeros.objects.filter(pk=id_mensajero, estado=True).first()
            if not mensajero:
                raise ReglaNegocioError(msg.MSG_MENSAJERO_INACTIVO, codigo="MENSAJERO_INACTIVO")

        factura = Facturas.objects.select_related("id_tipo_venta").filter(pk=id_factura).first()
        if not factura or not _es_factura_domicilio(factura):
            raise ReglaNegocioError(msg.MSG_FACTURA_INVALIDA, codigo="FACTURA_INVALIDA")
        if Entregas.objects.filter(id_factura=factura, estado__in=ESTADOS_BANDEJA).exists():
            raise ReglaNegocioError(msg.MSG_FACTURA_INVALIDA, codigo="ENTREGA_ACTIVA")

        uid = _usuario_id(ctx)
        if not uid:
            raise ReglaNegocioError(msg.MSG_CREAR_FALLA, codigo="NO_AUTORIZADO")

        estado_inicial = "ASIGNADO" if mensajero else "PENDIENTE"
        ahora = timezone.now()
        try:
            entrega = Entregas.objects.create(
                id_factura=factura,
                direccion=direccion,
                telefono_contacto=telefono,
                valor_cobrado_cliente=valor_cli,
                valor_pagado_mensajero=valor_msg,
                observaciones=observaciones,
                id_mensajero=mensajero,
                fecha_asignacion=ahora if mensajero else None,
                estado=estado_inicial,
            )
        except IntegrityError as exc:
            raise ReglaNegocioError(msg.MSG_FACTURA_INVALIDA, codigo="ENTREGA_ACTIVA") from exc

        Historial_entregas.objects.create(
            id_entrega=entrega,
            estado_anterior=None,
            estado_nuevo=estado_inicial,
            id_usuario_id=uid,
            observaciones=observaciones or ("Asignación en punto de venta" if mensajero else ""),
        )
        ser = _serializar_entrega(entrega)
        _auditar(ctx, "CREAR_DOMICILIO", "Entregas", entrega.id_entrega, None, ser, self._audit)
        return {
            "mensaje": msg.MSG_CREADO.format(consecutivo=_consecutivo_factura(factura)),
            "item": ser,
        }

    @transaction.atomic
    def asignar_mensajero(self, ctx: AuthContext, id_entrega: int, datos: dict[str, Any]) -> dict[str, Any]:
        id_mensajero = int(datos.get("id_mensajero") or 0)
        if not id_mensajero:
            raise ReglaNegocioError(msg.MSG_MENSAJERO_REQUERIDO, codigo="VALIDACION")
        mensajero = Mensajeros.objects.filter(pk=id_mensajero).first()
        if not mensajero or not mensajero.estado:
            raise ReglaNegocioError(msg.MSG_MENSAJERO_INACTIVO, codigo="MENSAJERO_INACTIVO")

        entrega = Entregas.objects.select_for_update().filter(pk=id_entrega).first()
        if not entrega:
            raise ReglaNegocioError(msg.MSG_ASIGNAR_FALLA, codigo="NO_ENCONTRADO")
        if entrega.estado not in ESTADOS_BANDEJA:
            raise ReglaNegocioError(msg.MSG_ASIGNAR_FALLA, codigo="ESTADO_INVALIDO")

        uid = _usuario_id(ctx)
        if not uid:
            raise ReglaNegocioError(msg.MSG_ASIGNAR_FALLA, codigo="NO_AUTORIZADO")

        antes = _serializar_entrega(entrega)
        estado_anterior = entrega.estado
        ahora = timezone.now()
        entrega.id_mensajero = mensajero
        entrega.fecha_asignacion = ahora
        if entrega.estado == "PENDIENTE":
            entrega.estado = "ASIGNADO"
        entrega.version_fila += 1
        entrega.save()

        obs = (datos.get("observaciones") or "").strip()
        Historial_entregas.objects.create(
            id_entrega=entrega,
            estado_anterior=estado_anterior if estado_anterior != entrega.estado else estado_anterior,
            estado_nuevo=entrega.estado,
            id_usuario_id=uid,
            observaciones=obs or "Asignación de mensajero",
        )
        despues = _serializar_entrega(entrega)
        _auditar(ctx, "ASIGNAR_MENSAJERO", "Entregas", entrega.id_entrega, antes, despues, self._audit)
        return {"mensaje": msg.MSG_ASIGNADO, "item": despues}

    @transaction.atomic
    def cambiar_estado(self, ctx: AuthContext, id_entrega: int, datos: dict[str, Any]) -> dict[str, Any]:
        nuevo = (datos.get("estado") or "").strip().upper()
        if not nuevo:
            raise ReglaNegocioError(msg.MSG_CAMPOS_OBLIGATORIOS, codigo="VALIDACION")

        entrega = Entregas.objects.select_for_update().select_related("id_mensajero").filter(pk=id_entrega).first()
        if not entrega:
            raise ReglaNegocioError(msg.MSG_ESTADO_FALLA, codigo="NO_ENCONTRADO")

        actual = entrega.estado
        if not transicion_permitida(actual, nuevo):
            raise ReglaNegocioError(
                msg.MSG_TRANSICION.format(
                    actual=ESTADOS_ETIQUETA.get(actual, actual),
                    nuevo=ESTADOS_ETIQUETA.get(nuevo, nuevo),
                ),
                codigo="TRANSICION_INVALIDA",
            )
        if nuevo == "EN_CAMINO" and not entrega.id_mensajero_id:
            raise ReglaNegocioError(msg.MSG_EN_CAMINO_SIN_MENSAJERO, codigo="MENSAJERO_REQUERIDO")

        uid = _usuario_id(ctx)
        if not uid:
            raise ReglaNegocioError(msg.MSG_ESTADO_FALLA, codigo="NO_AUTORIZADO")

        antes = _serializar_entrega(entrega)
        ahora = timezone.now()
        entrega.estado = nuevo
        if nuevo == "EN_CAMINO":
            entrega.fecha_salida = ahora
        if nuevo == "ENTREGADO":
            entrega.fecha_entrega = ahora
        entrega.version_fila += 1
        entrega.save()

        obs = (datos.get("observaciones") or "").strip()
        Historial_entregas.objects.create(
            id_entrega=entrega,
            estado_anterior=actual,
            estado_nuevo=nuevo,
            id_usuario_id=uid,
            observaciones=obs,
        )
        despues = _serializar_entrega(entrega)
        _auditar(ctx, "CAMBIAR_ESTADO_DOMICILIO", "Entregas", entrega.id_entrega, antes, despues, self._audit)
        etiqueta = ESTADOS_ETIQUETA.get(nuevo, nuevo)
        return {"mensaje": msg.MSG_ESTADO_OK.format(estado=etiqueta), "item": despues}

    def bandeja(
        self,
        estado: str | None,
        id_mensajero: int | None,
        fecha_desde: str | None,
        fecha_hasta: str | None,
        id_sede: int | None,
        orden: str,
        page: int,
        page_size: int,
        vista: str | None = None,
    ) -> dict[str, Any]:
        vista_norm = (vista or "activos").strip().lower()
        filtros_vista: dict[str, tuple[str, ...] | None] = {
            "activos": ESTADOS_BANDEJA,
            "entregado": ("ENTREGADO",),
            "cancelado": ("CANCELADO",),
            "todos": None,
        }
        estados_vista = filtros_vista.get(vista_norm, ESTADOS_BANDEJA)
        qs = Entregas.objects.select_related(
            "id_factura__id_cliente", "id_factura__id_sede", "id_mensajero"
        )
        if estados_vista is not None:
            qs = qs.filter(estado__in=estados_vista)
        if estado:
            est_up = estado.upper()
            if estados_vista is None or est_up in estados_vista:
                qs = qs.filter(estado=est_up)
        if id_mensajero:
            qs = qs.filter(id_mensajero_id=id_mensajero)
        if id_sede:
            qs = qs.filter(id_factura__id_sede_id=id_sede)
        if fecha_desde:
            qs = qs.filter(fecha_solicitud__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_solicitud__date__lte=fecha_hasta)

        asc = orden == "asc"
        qs = qs.order_by("fecha_solicitud" if asc else "-fecha_solicitud")
        total = qs.count()
        start = (page - 1) * page_size
        items = [_serializar_entrega(e) for e in qs[start : start + page_size]]
        if not total:
            return {"mensaje": msg.MSG_BANDEJA_VACIA, "items": [], "total": 0, "page": page, "page_size": page_size}
        return {
            "mensaje": msg.MSG_BANDEJA.format(n=total),
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def detalle(self, id_entrega: int) -> dict[str, Any]:
        entrega = (
            Entregas.objects.select_related("id_factura__id_cliente", "id_mensajero")
            .prefetch_related("historial")
            .filter(pk=id_entrega)
            .first()
        )
        if not entrega:
            raise ReglaNegocioError(msg.MSG_BANDEJA_FALLA, codigo="NO_ENCONTRADO")
        return {"item": _serializar_entrega(entrega, incluir_historial=True)}

    def mensajeros_activos(self) -> dict[str, Any]:
        items = [
            {"id_mensajero": m.id_mensajero, "label": f"{m.nombre} {m.apellido}".strip()}
            for m in Mensajeros.objects.filter(estado=True).order_by("nombre", "apellido")
        ]
        return {"items": items}

    def mensajeros_listar(self, q: str, estado: str | None, page: int, page_size: int) -> dict[str, Any]:
        qs = Mensajeros.objects.all()
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(apellido__icontains=texto)
                | Q(documento__icontains=texto)
                | Q(telefono__icontains=texto)
            )
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)
        total = qs.count()
        start = (page - 1) * page_size
        items = [_serializar_mensajero(m) for m in qs.order_by("nombre", "apellido")[start : start + page_size]]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @transaction.atomic
    def mensajero_crear(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        nombre = (datos.get("nombre") or "").strip()
        apellido = (datos.get("apellido") or "").strip()
        documento = (datos.get("documento") or "").strip()
        telefono = (datos.get("telefono") or "").strip()
        fecha_s = (datos.get("fecha_inicio") or "").strip()
        if not all([nombre, apellido, documento, telefono, fecha_s]):
            raise ReglaNegocioError(msg.MSG_CAMPOS_OBLIGATORIOS, codigo="VALIDACION")
        try:
            fecha_inicio = timezone.datetime.fromisoformat(fecha_s).date()
        except ValueError as exc:
            raise ReglaNegocioError(msg.MSG_CAMPOS_OBLIGATORIOS, codigo="VALIDACION") from exc
        if fecha_inicio > timezone.localdate():
            raise ReglaNegocioError(msg.MSG_FECHA_INICIO, codigo="FECHA_INVALIDA")
        tarifa_raw = datos.get("tarifa_promedio")
        tarifa = Decimal("0") if tarifa_raw in (None, "") else _decimal(tarifa_raw, "tarifa_promedio")
        observaciones = (datos.get("observaciones") or "").strip()
        estado = bool(datos.get("estado", True))

        try:
            m = Mensajeros.objects.create(
                nombre=nombre[:255],
                apellido=apellido[:255],
                documento=documento[:20],
                telefono=telefono[:20],
                fecha_inicio=fecha_inicio,
                tarifa_promedio=tarifa,
                observaciones=observaciones,
                estado=estado,
            )
        except IntegrityError as exc:
            raise ReglaNegocioError(msg.MSG_MENSAJERO_FALLA, codigo="DUPLICADO") from exc

        ser = _serializar_mensajero(m)
        _auditar(ctx, "CREAR_MENSAJERO", "Mensajeros", m.id_mensajero, None, ser, self._audit)
        return {"mensaje": msg.MSG_MENSAJERO_CREADO, "item": ser}

    @transaction.atomic
    def mensajero_actualizar(self, ctx: AuthContext, id_mensajero: int, datos: dict[str, Any]) -> dict[str, Any]:
        m = Mensajeros.objects.select_for_update().filter(pk=id_mensajero).first()
        if not m:
            raise ReglaNegocioError(msg.MSG_MENSAJERO_EDITAR_FALLA, codigo="NO_ENCONTRADO")
        version = int(datos.get("version_fila") or 0)
        if version != m.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")

        nombre = (datos.get("nombre") or m.nombre).strip()
        apellido = (datos.get("apellido") or m.apellido).strip()
        documento = (datos.get("documento") or m.documento).strip()
        telefono = (datos.get("telefono") or m.telefono).strip()
        fecha_s = (datos.get("fecha_inicio") or m.fecha_inicio.isoformat()).strip()
        if not all([nombre, apellido, documento, telefono, fecha_s]):
            raise ReglaNegocioError(msg.MSG_CAMPOS_OBLIGATORIOS, codigo="VALIDACION")
        try:
            fecha_inicio = timezone.datetime.fromisoformat(fecha_s).date()
        except ValueError as exc:
            raise ReglaNegocioError(msg.MSG_CAMPOS_OBLIGATORIOS, codigo="VALIDACION") from exc
        if fecha_inicio > timezone.localdate():
            raise ReglaNegocioError(msg.MSG_FECHA_INICIO, codigo="FECHA_INVALIDA")
        tarifa_raw = datos.get("tarifa_promedio", m.tarifa_promedio)
        tarifa = _decimal(tarifa_raw, "tarifa_promedio")
        observaciones = (datos.get("observaciones") if "observaciones" in datos else m.observaciones) or ""
        estado = bool(datos.get("estado", m.estado))

        antes = _serializar_mensajero(m)
        m.nombre = nombre[:255]
        m.apellido = apellido[:255]
        m.documento = documento[:20]
        m.telefono = telefono[:20]
        m.fecha_inicio = fecha_inicio
        m.tarifa_promedio = tarifa
        m.observaciones = observaciones
        m.estado = estado
        m.version_fila += 1
        try:
            m.save()
        except IntegrityError as exc:
            raise ReglaNegocioError(msg.MSG_MENSAJERO_EDITAR_FALLA, codigo="DUPLICADO") from exc

        despues = _serializar_mensajero(m)
        _auditar(ctx, "EDITAR_MENSAJERO", "Mensajeros", m.id_mensajero, antes, despues, self._audit)
        return {"mensaje": msg.MSG_MENSAJERO_ACTUALIZADO, "item": despues}

    def historial(
        self,
        id_mensajero: int | None,
        id_cliente: int | None,
        fecha_desde: str | None,
        fecha_hasta: str | None,
        estado: str | None,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        qs = Entregas.objects.select_related(
            "id_factura__id_cliente", "id_mensajero"
        ).filter(estado__in=("ENTREGADO", "CANCELADO", "PENDIENTE", "ASIGNADO", "EN_CAMINO"))
        if id_mensajero:
            qs = qs.filter(id_mensajero_id=id_mensajero)
        if id_cliente:
            qs = qs.filter(id_factura__id_cliente_id=id_cliente)
        if estado:
            qs = qs.filter(estado=estado.upper())
        if fecha_desde:
            qs = qs.filter(fecha_solicitud__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_solicitud__date__lte=fecha_hasta)

        qs = qs.order_by("-fecha_solicitud")
        total = qs.count()
        start = (page - 1) * page_size
        items = [_serializar_entrega(e) for e in qs[start : start + page_size]]
        if not total:
            return {
                "mensaje": msg.MSG_HISTORIAL_VACIO,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }
        return {
            "mensaje": msg.MSG_HISTORIAL.format(n=len(items), total=total),
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
