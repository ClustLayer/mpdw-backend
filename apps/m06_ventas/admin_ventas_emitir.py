"""Emisión, consulta, anulación y devolución de facturas (Épica 8)."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.db.models import Q

from apps.m02_sedes.models import Sedes
from apps.m05_clientes.models import Clientes
from apps.m06_ventas import mensajes as msg
from apps.m06_ventas.models import (
    Descuentos_factura,
    Detalle_devolucion,
    Detalle_factura,
    Devoluciones,
    Facturas,
    Facturas_electronicas,
    Pagos,
    Tipos_venta,
)
from apps.m06_ventas.ventas_calculo import (
    aplicar_descuento_general,
    pct_descuento_acumulado,
    totales_factura,
)
from contratos.dtos import AuditoriaDTO
from contratos.excepciones import ReglaNegocioError

if TYPE_CHECKING:
    from apps.m06_ventas.admin_ventas_service import AdminVentasService
    from contratos.dtos import AuthContext


def emitir_factura(
    svc: AdminVentasService, ctx: AuthContext, body: dict[str, Any]
) -> dict[str, Any]:
    lineas_in = body.get("lineas") or []
    if not lineas_in:
        raise ReglaNegocioError("Agregue al menos un producto.")
    id_sede = int(body["id_sede"])
    id_tipo = int(body["id_tipo_venta"])
    sede = Sedes.objects.get(pk=id_sede, estado=True)
    Tipos_venta.objects.get(pk=id_tipo, estado=True)
    svc._asegurar_jornada(ctx, id_sede)

    lineas = svc._parse_lineas(lineas_in)
    desc_general = body.get("descuento_general")
    if desc_general and not (desc_general.get("motivo") or "").strip():
        raise ReglaNegocioError(msg.MSG_MOTIVO_DESCUENTO)
    pct = pct_descuento_acumulado(lineas_in, desc_general)
    lineas = aplicar_descuento_general(lineas, desc_general)
    tot = totales_factura(lineas)
    necesita_auth = pct > Decimal("10") or tot["margen"] < 0
    if necesita_auth:
        svc._validar_autorizacion(body)

    pagos_in = body.get("pagos") or []
    pagos_norm = svc._validar_pagos(pagos_in, tot["total"])

    id_cliente = body.get("id_cliente")
    comprador_correo = (body.get("comprador_correo") or "").strip()
    if comprador_correo and not __import__("re").match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$", comprador_correo
    ):
        raise ReglaNegocioError(msg.MSG_CORREO)
    if id_cliente:
        Clientes.objects.get(pk=int(id_cliente), estado=True)

    clave = body.get("clave_idempotencia")
    if clave and Facturas.objects.filter(clave_idempotencia=clave).exists():
        existente = Facturas.objects.get(clave_idempotencia=clave)
        return {
            "factura": svc._factura_dict(existente, True),
            "mensaje": msg.MSG_EMITIDA.format(
                consecutivo=existente.serie + "-" + existente.numero_factura
            ),
        }

    try:
        with transaction.atomic():
            for ln in lineas:
                if ln["inventario_habilitado"]:
                    pid = int(ln["id_producto"])
                    cant = Decimal(str(ln["cantidad"]))
                    inv = (
                        __import__("apps.m04_inventario.models", fromlist=["Inventarios"])
                        .Inventarios.objects.filter(id_producto_id=pid, id_sede_id=id_sede)
                        .first()
                    )
                    disp = inv.cantidad_actual if inv else Decimal("0")
                    if disp < cant:
                        raise ReglaNegocioError(
                            msg.MSG_STOCK_INSUFICIENTE.format(n=int(disp), producto=ln["nombre"]),
                        )

            serie, numero = svc._consecutivo(sede)
            factura = Facturas.objects.create(
                id_sede_id=id_sede,
                serie=serie,
                numero_factura=numero,
                id_cliente_id=int(id_cliente) if id_cliente else None,
                id_usuario_id=ctx.id_usuario,
                id_tipo_venta_id=id_tipo,
                subtotal=tot["subtotal"],
                descuento=tot["descuento"],
                impuesto=tot["impuesto"],
                total=tot["total"],
                estado="EMITIDA",
                requiere_factura_electronica=bool(body.get("requiere_factura_electronica")),
                requiere_revision_gerencial=necesita_auth,
                margen_negativo=tot["margen"] < 0,
                comprador_nombre=(body.get("comprador_nombre") or "")[:255],
                comprador_documento=(body.get("comprador_documento") or "")[:30],
                comprador_telefono=(body.get("comprador_telefono") or "")[:20],
                comprador_correo=comprador_correo[:255],
                observaciones=(body.get("observaciones") or "")[:2000],
                clave_idempotencia=clave or None,
            )
            ref = f"{serie}-{numero}"
            for ln in lineas:
                Detalle_factura.objects.create(
                    id_factura=factura,
                    id_producto_id=int(ln["id_producto"]),
                    cantidad=ln["cantidad"],
                    precio_unitario=ln["precio_unitario"],
                    descuento_porcentaje=ln.get("descuento_porcentaje") or 0,
                    descuento_valor=ln.get("descuento_valor") or 0,
                    iva_porcentaje=ln.get("iva_porcentaje") or 0,
                    iva_monto=ln.get("iva_monto") or 0,
                    costo_unitario=ln.get("costo_unitario") or 0,
                    subtotal=ln["total_linea"],
                )
                if ln["inventario_habilitado"]:
                    svc._bajar_stock(
                        ctx, id_sede, int(ln["id_producto"]), Decimal(str(ln["cantidad"])), ref
                    )

            if desc_general and (desc_general.get("motivo") or "").strip():
                Descuentos_factura.objects.create(
                    id_factura=factura,
                    tipo_descuento=(desc_general.get("tipo_descuento") or "PORCENTAJE").upper(),
                    porcentaje=Decimal(str(desc_general.get("porcentaje") or 0)),
                    valor=Decimal(str(desc_general.get("valor") or 0)),
                    motivo=desc_general["motivo"][:255],
                )

            for p in pagos_norm:
                Pagos.objects.create(
                    id_factura=factura,
                    id_metodo_pago=p["metodo"],
                    valor=p["valor"],
                    referencia=p["referencia"],
                )

            if factura.requiere_factura_electronica:
                Facturas_electronicas.objects.create(id_factura=factura, estado="PENDIENTE")

            if necesita_auth:
                svc._audit.registrar(
                    AuditoriaDTO(
                        id_usuario=ctx.id_usuario,
                        accion="REVISION_GERENCIAL",
                        entidad="Facturas",
                        id_entidad=int(factura.id_factura),
                        datos_antes=None,
                        datos_despues={
                            "requiere_revision_gerencial": True,
                            "pct_descuento": float(pct),
                        },
                        motivo="REVISION_GERENCIAL",
                        id_correlacion=ctx.id_correlacion,
                        ip=ctx.ip,
                        user_agent=ctx.user_agent,
                    )
                )

            svc._audit.registrar(
                AuditoriaDTO(
                    id_usuario=ctx.id_usuario,
                    accion="EMISION_FACTURA",
                    entidad="Facturas",
                    id_entidad=int(factura.id_factura),
                    datos_antes=None,
                    datos_despues={"consecutivo": ref, "total": float(tot["total"])},
                    motivo="EMISION_FACTURA",
                    id_correlacion=ctx.id_correlacion,
                    ip=ctx.ip,
                    user_agent=ctx.user_agent,
                )
            )
    except ReglaNegocioError:
        raise
    except Exception as exc:
        raise ReglaNegocioError(msg.MSG_EMITIR_FALLA, codigo="ERROR_TRANSACCION") from exc

    factura = Facturas.objects.select_related(
        "id_sede", "id_tipo_venta", "id_cliente", "id_usuario"
    ).get(pk=factura.id_factura)
    return {
        "factura": svc._factura_dict(factura, True),
        "mensaje": msg.MSG_EMITIDA.format(consecutivo=ref),
        "cambio": float(max(Decimal("0"), sum(p["valor"] for p in pagos_norm) - tot["total"])),
    }


def listar_facturas(
    svc: AdminVentasService, ctx: AuthContext, filtros: dict[str, str], page: int, page_size: int
) -> dict[str, Any]:
    qs = Facturas.objects.select_related("id_sede", "id_tipo_venta", "id_cliente", "id_usuario")
    if not svc._permisos.tiene_permiso(ctx, "facturas", "Total"):
        qs = qs.filter(id_usuario_id=ctx.id_usuario)
    q = (filtros.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(numero_factura__icontains=q)
            | Q(serie__icontains=q)
            | Q(id_cliente__nombre__icontains=q)
            | Q(comprador_documento__icontains=q)
            | Q(comprador_nombre__icontains=q)
        )
    if filtros.get("estado"):
        qs = qs.filter(estado=filtros["estado"])
    if filtros.get("id_sede"):
        qs = qs.filter(id_sede_id=int(filtros["id_sede"]))
    if filtros.get("id_tipo_venta"):
        qs = qs.filter(id_tipo_venta_id=int(filtros["id_tipo_venta"]))
    if filtros.get("id_usuario"):
        qs = qs.filter(id_usuario_id=int(filtros["id_usuario"]))
    if filtros.get("margen_negativo") == "1" and svc._permisos.tiene_permiso(
        ctx, "facturas", "Total"
    ):
        qs = qs.filter(margen_negativo=True)
    desde = filtros.get("desde")
    hasta = filtros.get("hasta")
    if desde:
        qs = qs.filter(fecha_hora__date__gte=desde)
    if hasta:
        qs = qs.filter(fecha_hora__date__lte=hasta)
    total = qs.count()
    page_size = min(100, max(1, page_size))
    offset = (max(1, page) - 1) * page_size
    items = [svc._factura_dict(f) for f in qs.order_by("-fecha_hora")[offset : offset + page_size]]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "mensaje": msg.MSG_LISTADO_FACTURAS.format(n=len(items), total=total),
    }


def obtener_factura(svc: AdminVentasService, ctx: AuthContext, pk: int) -> dict[str, Any]:
    try:
        f = Facturas.objects.select_related(
            "id_sede", "id_tipo_venta", "id_cliente", "id_usuario"
        ).get(pk=pk)
    except Facturas.DoesNotExist as exc:
        raise ReglaNegocioError("Factura no encontrada.", codigo="NO_ENCONTRADO") from exc
    if f.id_usuario_id != ctx.id_usuario and not svc._permisos.tiene_permiso(
        ctx, "facturas", "Total"
    ):
        raise ReglaNegocioError("Sin permiso para ver esta factura.", codigo="NO_AUTORIZADO")
    return {"factura": svc._factura_dict(f, True)}


def anular_factura(
    svc: AdminVentasService, ctx: AuthContext, pk: int, body: dict[str, Any]
) -> dict[str, Any]:
    motivo = (body.get("motivo") or "").strip()
    if len(motivo) < 10:
        raise ReglaNegocioError(msg.MSG_MOTIVO_ANULACION)
    puede = ctx.rol_nombre == "Administrador" or svc._permisos.tiene_permiso(
        ctx, "facturas", "Total"
    )
    if not puede:
        raise ReglaNegocioError("Sin permiso para anular.", codigo="NO_AUTORIZADO")

    try:
        with transaction.atomic():
            f = Facturas.objects.select_for_update().select_related("id_sede").get(pk=pk)
            consecutivo = f"{f.serie}-{f.numero_factura}"
            if f.estado == "ANULADA":
                raise ReglaNegocioError(msg.MSG_ANULADA_YA.format(consecutivo=consecutivo))
            if not svc._jornada_abierta(f.id_sede_id) and ctx.rol_nombre != "Administrador":
                raise ReglaNegocioError(msg.MSG_CAJA_CERRADA)

            ref = consecutivo
            for d in f.detalles.select_related("id_producto"):
                if d.id_producto.inventario_habilitado:
                    svc._subir_stock(
                        ctx,
                        f.id_sede_id,
                        d.id_producto_id,
                        d.cantidad - d.cantidad_devuelta,
                        "entrada_anulacion",
                        ref,
                    )

            f.estado = "ANULADA"
            f.observaciones = f"{f.observaciones}\n[ANULACIÓN]: {motivo}".strip()[:4000]
            f.version_fila += 1
            f.save(update_fields=["estado", "observaciones", "version_fila"])

            fe = Facturas_electronicas.objects.filter(id_factura_id=f.id_factura).first()
            if fe:
                fe.estado = "PENDIENTE"
                fe.tipo_nota = "NOTA_CREDITO"
                fe.observacion = f"Anulación factura {consecutivo}"
                fe.save(update_fields=["estado", "tipo_nota", "observacion"])

            svc._audit.registrar(
                AuditoriaDTO(
                    id_usuario=ctx.id_usuario,
                    accion="ANULACION_FACTURA",
                    entidad="Facturas",
                    id_entidad=int(f.id_factura),
                    datos_antes={"estado": "EMITIDA"},
                    datos_despues={"estado": "ANULADA", "motivo": motivo},
                    motivo=motivo[:255],
                    id_correlacion=ctx.id_correlacion,
                    ip=ctx.ip,
                    user_agent=ctx.user_agent,
                )
            )
    except ReglaNegocioError:
        raise
    except Exception as exc:
        raise ReglaNegocioError(msg.MSG_ANULAR_FALLA) from exc

    return {"mensaje": msg.MSG_ANULADA.format(consecutivo=consecutivo)}


def devolucion_parcial(
    svc: AdminVentasService, ctx: AuthContext, pk: int, body: dict[str, Any]
) -> dict[str, Any]:
    if ctx.rol_nombre not in ("Administrador", "Gerente"):
        raise ReglaNegocioError("Sin permiso para devoluciones.", codigo="NO_AUTORIZADO")
    motivo = (body.get("motivo") or "").strip()
    if not motivo:
        raise ReglaNegocioError(msg.MSG_MOTIVO_DEVOLUCION)
    lineas = body.get("lineas") or []
    seleccion = [ln for ln in lineas if Decimal(str(ln.get("cantidad") or 0)) > 0]
    if not seleccion:
        raise ReglaNegocioError(msg.MSG_DEVOLUCION_SIN_LINEA)

    try:
        with transaction.atomic():
            f = Facturas.objects.select_for_update().get(pk=pk)
            if f.estado == "ANULADA":
                raise ReglaNegocioError("La factura está anulada.")
            total_dev = Decimal("0")
            dev = Devoluciones.objects.create(
                id_factura=f, id_usuario_id=ctx.id_usuario, motivo=motivo[:255], total=0
            )
            ref = f"{f.serie}-{f.numero_factura}"
            for ln in seleccion:
                det = (
                    Detalle_factura.objects.select_for_update()
                    .select_related("id_producto")
                    .get(pk=int(ln["id_detalle"]), id_factura_id=f.id_factura)
                )
                qty = Decimal(str(ln["cantidad"]))
                pendiente = det.cantidad - det.cantidad_devuelta
                if qty > pendiente:
                    raise ReglaNegocioError(msg.MSG_DEVOLUCION_CANTIDAD)
                valor = (qty * det.precio_unitario).quantize(Decimal("0.01"))
                total_dev += valor
                det.cantidad_devuelta += qty
                det.save(update_fields=["cantidad_devuelta"])
                Detalle_devolucion.objects.create(
                    id_devolucion=dev, id_detalle_factura=det, cantidad=qty, valor=valor
                )
                if det.id_producto.inventario_habilitado:
                    svc._subir_stock(
                        ctx, f.id_sede_id, det.id_producto_id, qty, "entrada_devolucion", ref
                    )

            dev.total = total_dev
            dev.save(update_fields=["total"])
            f.estado = "DEVOLUCION_PARCIAL"
            f.version_fila += 1
            f.save(update_fields=["estado", "version_fila"])

            svc._audit.registrar(
                AuditoriaDTO(
                    id_usuario=ctx.id_usuario,
                    accion="DEVOLUCION_PARCIAL",
                    entidad="Facturas",
                    id_entidad=int(f.id_factura),
                    datos_antes=None,
                    datos_despues={"total_devuelto": float(total_dev), "motivo": motivo},
                    motivo=motivo[:255],
                    id_correlacion=ctx.id_correlacion,
                    ip=ctx.ip,
                    user_agent=ctx.user_agent,
                )
            )
    except ReglaNegocioError:
        raise
    except Exception as exc:
        raise ReglaNegocioError(msg.MSG_DEVOLUCION_FALLA) from exc

    return {"mensaje": msg.MSG_DEVOLUCION_OK, "total_devuelto": float(total_dev)}


def editar_factura(
    svc: AdminVentasService, ctx: AuthContext, pk: int, body: dict[str, Any]
) -> dict[str, Any]:
    if ctx.rol_nombre != "Administrador":
        raise ReglaNegocioError("Sin permiso para editar.", codigo="NO_AUTORIZADO")
    version = int(body.get("version_fila") or 0)
    try:
        with transaction.atomic():
            f = Facturas.objects.select_for_update().get(pk=pk)
            if f.version_fila != version:
                raise ReglaNegocioError(
                    "La factura fue modificada por otro usuario.", codigo="CONCURRENCIA"
                )
            if f.estado not in ("BORRADOR", "PENDIENTE_PAGO"):
                raise ReglaNegocioError(msg.MSG_NO_EDITABLE)
            if not svc._jornada_abierta(f.id_sede_id):
                raise ReglaNegocioError(msg.MSG_NO_EDITABLE)

            anterior = {"observaciones": f.observaciones, "id_cliente": f.id_cliente_id}
            if "observaciones" in body:
                f.observaciones = (body.get("observaciones") or "")[:4000]
            if "id_cliente" in body:
                cid = body.get("id_cliente")
                f.id_cliente_id = int(cid) if cid else None
            if f.estado == "BORRADOR" and body.get("pagos"):
                Pagos.objects.filter(id_factura=f).delete()
                pagos_norm = svc._validar_pagos(body["pagos"], f.total)
                for p in pagos_norm:
                    Pagos.objects.create(
                        id_factura=f,
                        id_metodo_pago=p["metodo"],
                        valor=p["valor"],
                        referencia=p["referencia"],
                    )

            f.version_fila += 1
            f.save()
            svc._audit.registrar(
                AuditoriaDTO(
                    id_usuario=ctx.id_usuario,
                    accion="EDICION_FACTURA",
                    entidad="Facturas",
                    id_entidad=int(f.id_factura),
                    datos_antes=anterior,
                    datos_despues={"observaciones": f.observaciones, "id_cliente": f.id_cliente_id},
                    motivo="EDICION_FACTURA",
                    id_correlacion=ctx.id_correlacion,
                    ip=ctx.ip,
                    user_agent=ctx.user_agent,
                )
            )
    except ReglaNegocioError:
        raise
    except Exception as exc:
        raise ReglaNegocioError(msg.MSG_EDITAR_FALLA) from exc

    return {"mensaje": msg.MSG_ACTUALIZADA, "factura": svc._factura_dict(f, True)}
