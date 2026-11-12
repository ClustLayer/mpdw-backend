"""Backoffice directorio de clientes y Habeas Data (HU 37–42)."""

from __future__ import annotations

import re
from typing import Any

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.m01_identidad.models import Usuarios
from apps.m05_clientes.mensajes import (
    MSG_ACTUALIZADO,
    MSG_ACTUALIZAR_ERROR,
    MSG_CONCURRENCIA,
    MSG_CORREO,
    MSG_CREADO,
    MSG_CREAR_ERROR,
    MSG_DUPLICADO_TEL,
    MSG_HISTORIAL,
    MSG_HISTORIAL_ERROR,
    MSG_HISTORIAL_VACIO,
    MSG_LISTADO,
    MSG_OBLIGATORIOS,
    MSG_SIN_COINCIDENCIAS,
    MSG_TELEFONO,
    MSG_TIPO_ACTUALIZADO,
    MSG_TIPO_COMUN_DUP,
    MSG_TIPO_COMUN_PROTEGIDO,
    MSG_TIPO_CREADO,
    MSG_TIPO_NOMBRE_OBL,
)
from apps.m05_clientes.models import Clientes, Tipos_cliente
from apps.m06_ventas.models import Detalle_factura, Facturas
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

E164_RE = re.compile(r"^\+?[1-9]\d{6,14}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ESTADOS_ANULADOS = frozenset({"ANULADA", "anulada", "Anulada"})


def _nombre_completo(c: Clientes) -> str:
    return f"{c.nombre} {c.apellido}".strip()


def _validar_e164(valor: str) -> str:
    t = (valor or "").strip()
    if not t or not E164_RE.match(t):
        raise ReglaNegocioError(MSG_TELEFONO, codigo="FORMATO_TELEFONO")
    return t if t.startswith("+") else f"+{t}"


def _validar_correo(valor: str) -> str:
    t = (valor or "").strip()
    if not t:
        return ""
    if not EMAIL_RE.match(t):
        raise ReglaNegocioError(MSG_CORREO, codigo="FORMATO_CORREO")
    return t


def whatsapp_habilitado(c: Clientes) -> tuple[bool, str, str]:
    """Devuelve (habilitado, url wa.me, motivo deshabilitado)."""
    if not c.tiene_whatsapp:
        return False, "", ""
    tel = (c.numero_telefono or "").strip()
    if not tel:
        return False, "", "El cliente no tiene número de teléfono registrado."
    digits = re.sub(r"\D", "", tel)
    if len(digits) < 10 or not E164_RE.match(f"+{digits}"):
        return False, "", "El teléfono no cumple el formato internacional e.164."
    return True, f"https://wa.me/{digits}", ""


def _serializar_cliente(c: Clientes, *, dup: Clientes | None = None) -> dict[str, Any]:
    wa_ok, wa_url, wa_motivo = whatsapp_habilitado(c)
    data: dict[str, Any] = {
        "id_cliente": c.id_cliente,
        "nombre": c.nombre,
        "apellido": c.apellido,
        "nombre_completo": _nombre_completo(c),
        "numero_telefono": c.numero_telefono,
        "tiene_whatsapp": c.tiene_whatsapp,
        "direccion": c.direccion,
        "ciudad": c.ciudad,
        "documento": c.documento,
        "correo": c.correo,
        "observaciones": c.observaciones,
        "id_tipo_cliente": c.id_tipo_cliente_id,
        "tipo_nombre": c.id_tipo_cliente.nombre,
        "consentimiento_datos": c.consentimiento_datos,
        "fecha_consentimiento": c.fecha_consentimiento.isoformat() if c.fecha_consentimiento else None,
        "estado": c.estado,
        "version_fila": c.version_fila,
        "whatsapp_url": wa_url if wa_ok else "",
        "whatsapp_habilitado": wa_ok,
        "whatsapp_motivo": wa_motivo,
    }
    if dup is not None:
        data["coincidencia"] = {
            "id_cliente": dup.id_cliente,
            "nombre_completo": _nombre_completo(dup),
            "numero_telefono": dup.numero_telefono,
        }
    return data


def _usuario_id(ctx: AuthContext) -> int | None:
    if not ctx.id_usuario:  # pragma: no cover
        return None
    return ctx.id_usuario if Usuarios.objects.filter(pk=ctx.id_usuario).exists() else None


def _auditar(ctx: AuthContext, accion: str, entidad: str, entidad_id: int, antes: dict | None, despues: dict | None, audit: AuditService) -> None:
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


class AdminClientesService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def tipos_listado(self, solo_activos: bool = False) -> dict[str, Any]:
        qs = Tipos_cliente.objects.all().order_by("nombre")
        if solo_activos:
            qs = qs.filter(estado=True)
        items = [
            {
                "id_tipo_cliente": t.id_tipo_cliente,
                "nombre": t.nombre,
                "descripcion": t.descripcion,
                "estado": t.estado,
                "es_tipo_predeterminado": t.es_tipo_predeterminado,
                "version_fila": t.version_fila,
            }
            for t in qs
        ]
        return {"items": items}

    def tipo_predeterminado_id(self) -> int:
        t = Tipos_cliente.objects.filter(es_tipo_predeterminado=True).first()
        if t:
            return t.id_tipo_cliente
        com, _ = Tipos_cliente.objects.get_or_create(
            nombre="Común",
            defaults={"es_tipo_predeterminado": True, "estado": True, "descripcion": "Cliente general"},
        )
        if not com.es_tipo_predeterminado:
            com.es_tipo_predeterminado = True
            com.save(update_fields=["es_tipo_predeterminado"])
        return com.id_tipo_cliente

    def listar(self, q: str, id_tipo: int | None, estado: str | None, page: int, page_size: int) -> dict[str, Any]:
        qs = Clientes.objects.select_related("id_tipo_cliente")
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(apellido__icontains=texto)
                | Q(numero_telefono__icontains=texto)
                | Q(documento__icontains=texto)
                | Q(correo__icontains=texto)
            )
        if id_tipo:
            qs = qs.filter(id_tipo_cliente_id=id_tipo)
        est = (estado or "todos").lower()
        if est == "activo":
            qs = qs.filter(estado=True)
        elif est == "inactivo":
            qs = qs.filter(estado=False)
        total = qs.count()
        if total == 0 and texto:
            return {"items": [], "total": 0, "mensaje": MSG_SIN_COINCIDENCIAS, "page": page, "page_size": page_size}
        offset = max(0, (max(1, page) - 1) * page_size)
        filas = [_serializar_cliente(c) for c in qs.order_by("nombre", "apellido")[offset : offset + page_size]]
        return {
            "items": filas,
            "total": total,
            "mensaje": MSG_LISTADO.format(n=len(filas), total=total),
            "page": page,
            "page_size": page_size,
        }

    def obtener(self, pk: int) -> dict[str, Any]:
        c = Clientes.objects.select_related("id_tipo_cliente").get(pk=pk)
        data = _serializar_cliente(c)
        data["tiene_facturas"] = Facturas.objects.filter(id_cliente_id=pk).exclude(estado__in=ESTADOS_ANULADOS).exists()
        return data

    def _validar_payload(self, datos: dict[str, Any], *, crear: bool) -> dict[str, Any]:
        nombre = (datos.get("nombre") or "").strip()
        if not nombre:
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        telefono = _validar_e164(str(datos.get("numero_telefono") or ""))
        correo = _validar_correo(str(datos.get("correo") or ""))
        id_tipo = datos.get("id_tipo_cliente")
        if crear and not id_tipo:
            id_tipo = self.tipo_predeterminado_id()
        if not id_tipo:
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        if not Tipos_cliente.objects.filter(pk=int(id_tipo), estado=True).exists():
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="TIPO_INACTIVO")
        consent = bool(datos.get("consentimiento_datos"))
        payload = {
            "nombre": nombre[:255],
            "apellido": (datos.get("apellido") or "").strip()[:255],
            "numero_telefono": telefono,
            "tiene_whatsapp": bool(datos.get("tiene_whatsapp")),
            "direccion": (datos.get("direccion") or "").strip()[:255],
            "ciudad": (datos.get("ciudad") or "").strip()[:100],
            "documento": (datos.get("documento") or "").strip()[:30],
            "correo": correo,
            "observaciones": (datos.get("observaciones") or "").strip(),
            "id_tipo_cliente_id": int(id_tipo),
            "consentimiento_datos": consent,
        }
        if not crear:
            payload["estado"] = bool(datos.get("estado", True))
        return payload

    def verificar_telefono(self, telefono: str, excluir_id: int | None = None) -> dict[str, Any] | None:
        tel = _validar_e164(telefono)
        qs = Clientes.objects.filter(numero_telefono=tel)
        if excluir_id:
            qs = qs.exclude(pk=excluir_id)
        dup = qs.select_related("id_tipo_cliente").first()
        if not dup:
            return None
        return {"mensaje": MSG_DUPLICADO_TEL, "coincidencia": _serializar_cliente(dup)}

    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        norm = self._validar_payload(datos, crear=True)
        if not datos.get("confirmar_duplicado"):
            aviso = self.verificar_telefono(norm["numero_telefono"])
            if aviso:
                aviso["codigo"] = "TELEFONO_DUPLICADO"
                raise ReglaNegocioError(aviso["mensaje"], codigo="TELEFONO_DUPLICADO", detalles=[aviso["coincidencia"]])
        if norm["consentimiento_datos"]:
            norm["fecha_consentimiento"] = timezone.now()
        else:
            norm["fecha_consentimiento"] = None
        try:
            with transaction.atomic():
                c = Clientes.objects.create(**norm, estado=True)
                _auditar(
                    ctx,
                    "CREAR",
                    "Clientes",
                    c.id_cliente,
                    None,
                    _serializar_cliente(c),
                    self._audit,
                )
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_CREAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_CREADO, "cliente": _serializar_cliente(c)}

    def actualizar(self, ctx: AuthContext, pk: int, datos: dict[str, Any]) -> dict[str, Any]:
        try:
            c = Clientes.objects.select_related("id_tipo_cliente").get(pk=pk)
        except Clientes.DoesNotExist as exc:
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="NO_ENCONTRADO") from exc
        version = int(datos.get("version_fila") or 0)
        if version != c.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        norm = self._validar_payload(datos, crear=False)
        tiene_facturas = Facturas.objects.filter(id_cliente_id=pk).exclude(estado__in=ESTADOS_ANULADOS).exists()
        if tiene_facturas and (datos.get("documento") or "").strip() != (c.documento or "").strip():
            raise ReglaNegocioError(
                "El documento no puede modificarse porque el cliente tiene facturas registradas.",
                codigo="DOCUMENTO_BLOQUEADO",
            )
        if not datos.get("confirmar_duplicado"):
            aviso = self.verificar_telefono(norm["numero_telefono"], excluir_id=pk)
            if aviso:
                raise ReglaNegocioError(aviso["mensaje"], codigo="TELEFONO_DUPLICADO", detalles=[aviso["coincidencia"]])
        antes = _serializar_cliente(c)
        consent_prev = c.consentimiento_datos
        if norm["consentimiento_datos"] and not consent_prev:
            norm["fecha_consentimiento"] = timezone.now()
        elif not norm["consentimiento_datos"]:
            norm["fecha_consentimiento"] = c.fecha_consentimiento
        else:
            norm["fecha_consentimiento"] = c.fecha_consentimiento
        norm["estado"] = bool(datos.get("estado", c.estado))
        try:
            with transaction.atomic():
                for k, v in norm.items():
                    setattr(c, k, v)
                c.version_fila = int(c.version_fila) + 1
                c.save()
                _auditar(ctx, "EDITAR", "Clientes", c.id_cliente, antes, _serializar_cliente(c), self._audit)
        except Exception as exc:  # pragma: no cover
            raise ReglaNegocioError(MSG_ACTUALIZAR_ERROR, codigo="ERROR_INTERNO") from exc
        return {"mensaje": MSG_ACTUALIZADO, "cliente": _serializar_cliente(c)}

    def crear_tipo(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        nombre = (datos.get("nombre") or "").strip()
        if not nombre:
            raise ReglaNegocioError(MSG_TIPO_NOMBRE_OBL, codigo="CAMPOS_OBLIGATORIOS")
        if nombre.lower() == "común" or nombre.lower() == "comun":
            raise ReglaNegocioError(MSG_TIPO_COMUN_DUP, codigo="TIPO_COMUN")
        if Tipos_cliente.objects.filter(nombre__iexact=nombre).exists():
            raise ReglaNegocioError("Ya existe un tipo de cliente con este nombre.", codigo="NOMBRE_DUP")
        row = Tipos_cliente.objects.create(
            nombre=nombre[:50],
            descripcion=(datos.get("descripcion") or "").strip(),
            estado=True,
        )
        _auditar(ctx, "CREAR", "Tipos_cliente", row.id_tipo_cliente, None, {"nombre": row.nombre}, self._audit)
        return {
            "mensaje": MSG_TIPO_CREADO,
            "tipo": {
                "id_tipo_cliente": row.id_tipo_cliente,
                "nombre": row.nombre,
                "descripcion": row.descripcion,
                "estado": row.estado,
                "es_tipo_predeterminado": row.es_tipo_predeterminado,
                "version_fila": row.version_fila,
            },
        }

    def actualizar_tipo(self, ctx: AuthContext, pk: int, datos: dict[str, Any]) -> dict[str, Any]:
        row = Tipos_cliente.objects.get(pk=pk)
        if row.es_tipo_predeterminado:
            raise ReglaNegocioError(MSG_TIPO_COMUN_PROTEGIDO, codigo="TIPO_COMUN")
        version = int(datos.get("version_fila") or 0)
        if version != row.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        nombre = (datos.get("nombre") or row.nombre).strip()
        if not nombre:
            raise ReglaNegocioError(MSG_TIPO_NOMBRE_OBL, codigo="CAMPOS_OBLIGATORIOS")
        antes = {"nombre": row.nombre, "estado": row.estado}
        row.nombre = nombre[:50]
        row.descripcion = (datos.get("descripcion") or row.descripcion or "").strip()
        row.estado = bool(datos.get("estado", row.estado))
        row.version_fila = int(row.version_fila) + 1
        row.save()
        _auditar(ctx, "EDITAR", "Tipos_cliente", row.id_tipo_cliente, antes, {"nombre": row.nombre, "estado": row.estado}, self._audit)
        return {
            "mensaje": MSG_TIPO_ACTUALIZADO,
            "tipo": {
                "id_tipo_cliente": row.id_tipo_cliente,
                "nombre": row.nombre,
                "descripcion": row.descripcion,
                "estado": row.estado,
                "es_tipo_predeterminado": row.es_tipo_predeterminado,
                "version_fila": row.version_fila,
            },
        }

    def historial(
        self,
        ctx: AuthContext,
        pk: int,
        desde: str | None,
        hasta: str | None,
        page: int,
        page_size: int,
        incluir_metricas: bool,
    ) -> dict[str, Any]:
        try:
            c = Clientes.objects.select_related("id_tipo_cliente").get(pk=pk)
        except Clientes.DoesNotExist as exc:
            raise ReglaNegocioError(MSG_HISTORIAL_ERROR, codigo="NO_ENCONTRADO") from exc
        qs = Facturas.objects.filter(id_cliente_id=pk).exclude(estado__in=ESTADOS_ANULADOS).select_related("id_sede")
        if desde:
            qs = qs.filter(fecha_hora__date__gte=desde)
        if hasta:
            qs = qs.filter(fecha_hora__date__lte=hasta)
        total = qs.count()
        if total == 0:
            return {
                "cliente": _serializar_cliente(c),
                "items": [],
                "total": 0,
                "mensaje": MSG_HISTORIAL_VACIO,
                "resumen": {"total_comprado": 0, "num_compras": 0, "ultima_compra": None},
                "metricas": None,
            }
        offset = max(0, (max(1, page) - 1) * page_size)
        facturas = list(qs.order_by("-fecha_hora")[offset : offset + page_size])
        items = [
            {
                "id_factura": f.id_factura,
                "numero": f"{f.serie}-{f.numero_factura}",
                "fecha": f.fecha_hora.isoformat(),
                "sede": f.id_sede.nombre,
                "total": float(f.total),
                "estado": f.estado,
            }
            for f in facturas
        ]
        agg = qs.aggregate(s=Sum("total"), n=Count("id_factura"))
        ultima = qs.order_by("-fecha_hora").first()
        resumen = {
            "total_comprado": float(agg["s"] or 0),
            "num_compras": int(agg["n"] or 0),
            "ultima_compra": ultima.fecha_hora.isoformat() if ultima else None,
        }
        metricas = None
        if incluir_metricas and ctx.rol_nombre in ("Gerente", "Administrador"):
            fechas = list(qs.order_by("fecha_hora").values_list("fecha_hora", flat=True))
            dias_prom = 0.0
            if len(fechas) > 1:
                span = (fechas[-1] - fechas[0]).days or 1
                dias_prom = round(span / max(1, len(fechas) - 1), 1)
            ticket = float(agg["s"] or 0) / max(1, int(agg["n"] or 1))
            top = (
                Detalle_factura.objects.filter(id_factura__id_cliente_id=pk)
                .exclude(id_factura__estado__in=ESTADOS_ANULADOS)
                .values("id_producto__nombre")
                .annotate(unidades=Sum("cantidad"), monto=Sum("subtotal"))
                .order_by("-unidades")[:5]
            )
            metricas = {
                "monto_total": float(agg["s"] or 0),
                "frecuencia_compras": int(agg["n"] or 0),
                "ticket_promedio": round(ticket, 2),
                "dias_promedio_entre_compras": dias_prom,
                "productos_frecuentes": [
                    {
                        "nombre": row["id_producto__nombre"],
                        "unidades": float(row["unidades"] or 0),
                        "monto": float(row["monto"] or 0),
                    }
                    for row in top
                ],
            }
        return {
            "cliente": _serializar_cliente(c),
            "items": items,
            "total": total,
            "mensaje": MSG_HISTORIAL.format(n=len(items)),
            "resumen": resumen,
            "metricas": metricas,
            "page": page,
            "page_size": page_size,
        }
