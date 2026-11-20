"""Servicio de bandeja y gestión manual de facturación externa (sin DIAN)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.m01_identidad.models import Usuarios
from apps.m06_ventas import mensajes_fe as msg
from apps.m06_ventas.facturacion_externa_logica import ESTADOS_ETIQUETA, transicion_permitida
from apps.m06_ventas.models import Facturas, Facturas_electronicas
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError


def _usuario_id(ctx: AuthContext) -> int | None:
    if not ctx.id_usuario:
        return None
    if not Usuarios.objects.filter(pk=ctx.id_usuario).exists():
        return None
    return ctx.id_usuario


def _auditar(
    ctx: AuthContext,
    accion: str,
    entidad_id: int,
    antes: dict | None,
    despues: dict | None,
    audit: AuditService,
    motivo: str = "",
) -> None:
    audit.registrar(
        AuditoriaDTO(
            id_usuario=_usuario_id(ctx),
            accion=accion,
            entidad=msg.AUDIT_ENTIDAD,
            id_entidad=entidad_id,
            datos_antes=antes,
            datos_despues=despues,
            motivo=motivo or accion,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


def _nombre_cliente(factura: Facturas) -> str:
    c = factura.id_cliente
    if c:
        return f"{c.nombre} {c.apellido}".strip()
    return factura.comprador_nombre or "Sin cliente"


def _numero_factura(f: Facturas) -> str:
    return f"{f.serie}-{f.numero_factura}"


def _validar_url(url: str) -> str:
    t = (url or "").strip()
    if not t:
        return ""
    parsed = urlparse(t)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ReglaNegocioError(msg.MSG_URL_INVALIDA, codigo="VALIDACION")
    return t[:500]


def _serializar(fe: Facturas_electronicas, incluir_pdf: bool) -> dict[str, Any]:
    factura = fe.id_factura
    estado = (fe.estado or "PENDIENTE").strip().upper()
    item: dict[str, Any] = {
        "id_gestion_externa": fe.id_factura_electronica,
        "id_factura": factura.id_factura,
        "numero_factura": _numero_factura(factura),
        "cliente": _nombre_cliente(factura),
        "fecha_solicitud": fe.fecha_registro.isoformat(),
        "estado": estado,
        "estado_etiqueta": ESTADOS_ETIQUETA.get(estado, estado),
        "numero_electronico": (fe.referencia_externa or "").strip(),
        "observaciones": fe.observacion or "",
        "fecha_registro": fe.fecha_registro.isoformat(),
        "version_fila": fe.version_fila,
        "tiene_soporte_pdf": bool((fe.url_pdf or "").strip()) and estado == "GENERADA_EXTERNA",
    }
    if incluir_pdf and estado == "GENERADA_EXTERNA" and (fe.url_pdf or "").strip():
        item["url_pdf"] = fe.url_pdf.strip()
    return item


class AdminFacturacionExternaService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def bandeja(
        self,
        estado: str | None,
        fecha_desde: str | None,
        fecha_hasta: str | None,
        numero: str | None,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        qs = Facturas_electronicas.objects.select_related(
            "id_factura", "id_factura__id_cliente"
        ).filter(id_factura__requiere_factura_electronica=True)
        if estado:
            qs = qs.filter(estado=estado.strip().upper())
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        texto = (numero or "").strip()
        if texto:
            qs = qs.filter(
                Q(id_factura__numero_factura__icontains=texto)
                | Q(id_factura__serie__icontains=texto)
                | Q(referencia_externa__icontains=texto)
            )
        qs = qs.order_by("-fecha_registro")
        total = qs.count()
        start = (page - 1) * page_size
        page_items = list(qs[start : start + page_size])
        if not total:
            return {
                "mensaje": msg.MSG_BANDEJA_VACIA,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }
        return {
            "mensaje": msg.MSG_BANDEJA.format(n=len(page_items), total=total),
            "items": [_serializar(fe, incluir_pdf=False) for fe in page_items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def detalle(self, id_gestion: int) -> dict[str, Any]:
        fe = (
            Facturas_electronicas.objects.select_related("id_factura", "id_factura__id_cliente")
            .filter(pk=id_gestion)
            .first()
        )
        if not fe:
            raise ReglaNegocioError(msg.MSG_BANDEJA_FALLA, codigo="NO_ENCONTRADO")
        return {"item": _serializar(fe, incluir_pdf=False)}

    def url_soporte(self, id_gestion: int) -> dict[str, Any]:
        fe = Facturas_electronicas.objects.filter(pk=id_gestion).first()
        if not fe:
            raise ReglaNegocioError(msg.MSG_SOPORTE_NO, codigo="NO_ENCONTRADO")
        estado = (fe.estado or "").strip().upper()
        if estado != "GENERADA_EXTERNA":
            raise ReglaNegocioError(msg.MSG_SOPORTE_NO, codigo="ESTADO_INVALIDO")
        url = (fe.url_pdf or "").strip()
        if not url:
            raise ReglaNegocioError(msg.MSG_SOPORTE_NO, codigo="SIN_SOPORTE")
        return {"url_pdf": url}

    @transaction.atomic
    def actualizar_estado(self, ctx: AuthContext, id_gestion: int, datos: dict[str, Any]) -> dict[str, Any]:
        uid = _usuario_id(ctx)
        if not uid:
            raise ReglaNegocioError(msg.MSG_ESTADO_FALLA, codigo="NO_AUTORIZADO")

        fe = Facturas_electronicas.objects.select_for_update().filter(pk=id_gestion).first()
        if not fe:
            raise ReglaNegocioError(msg.MSG_ESTADO_FALLA, codigo="NO_ENCONTRADO")

        version = int(datos.get("version_fila") or 0)
        if version and version != fe.version_fila:
            raise ReglaNegocioError(msg.MSG_ESTADO_FALLA, codigo="CONCURRENCIA")

        nuevo = (datos.get("estado") or "").strip().upper()
        actual = (fe.estado or "PENDIENTE").strip().upper()
        if not nuevo:
            raise ReglaNegocioError(msg.MSG_ESTADO_FALLA, codigo="VALIDACION")
        if not transicion_permitida(actual, nuevo):
            raise ReglaNegocioError(
                msg.MSG_TRANSICION.format(
                    actual=ESTADOS_ETIQUETA.get(actual, actual),
                    nuevo=ESTADOS_ETIQUETA.get(nuevo, nuevo),
                ),
                codigo="TRANSICION_INVALIDA",
            )

        numero = (datos.get("numero_electronico") or fe.referencia_externa or "").strip()
        url_raw = datos.get("url_pdf")
        if url_raw is None:
            url_pdf = (fe.url_pdf or "").strip()
        else:
            url_pdf = _validar_url(str(url_raw))
        obs = (datos.get("observaciones") if "observaciones" in datos else fe.observacion) or ""
        obs = str(obs).strip()[:2000]

        if nuevo == "GENERADA_EXTERNA":
            if not numero:
                raise ReglaNegocioError(msg.MSG_NUMERO_REQUERIDO, codigo="VALIDACION")
            if len(numero) > 100:
                raise ReglaNegocioError(msg.MSG_NUMERO_LARGO, codigo="VALIDACION")

        antes = _serializar(fe, incluir_pdf=False)
        fe.estado = nuevo
        fe.referencia_externa = numero[:100]
        fe.url_pdf = url_pdf
        fe.observacion = obs
        fe.version_fila += 1
        if nuevo == "GENERADA_EXTERNA" and not fe.fecha_registro:
            fe.fecha_registro = timezone.now()
        fe.save()

        despues = _serializar(fe, incluir_pdf=False)
        _auditar(
            ctx,
            "CAMBIAR_ESTADO_FE_EXTERNA",
            fe.id_factura_electronica,
            antes,
            despues,
            self._audit,
            motivo=obs or f"Estado {actual} → {nuevo}",
        )
        etiqueta = ESTADOS_ETIQUETA.get(nuevo, nuevo)
        return {"mensaje": msg.MSG_ESTADO_OK.format(estado=etiqueta), "item": despues}
