"""POS, emisión ACID, consulta y posventa de facturas (Épica 8)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.m01_identidad.models import Usuarios
from apps.m01_identidad.services import PermissionService
from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Productos
from apps.m04_inventario.models import Inventarios, Movimientos_inventario
from apps.m06_ventas import mensajes as msg
from apps.m06_ventas.models import (
    Consecutivos,
    Facturas,
    Facturas_electronicas,
    Metodos_pago,
    Tipos_venta,
)
from apps.m06_ventas.ventas_calculo import calcular_lineas
from apps.m08_caja.models import Reportes_diarios
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuthContext
from contratos.excepciones import ReglaNegocioError

CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES_AUTORIZADORES = frozenset({"Administrador", "Gerente"})
TIPO_MOV_VENTA = "venta_pos"
TIPO_MOV_ANUL = "entrada_anulacion"
TIPO_MOV_DEV = "entrada_devolucion"


class AdminVentasService:
    def __init__(
        self, audit: AuditService | None = None, permisos: PermissionService | None = None
    ) -> None:
        self._audit = audit or AuditService()
        self._permisos = permisos or PermissionService()

    def catalogos_pos(self) -> dict[str, Any]:
        sedes = list(
            Sedes.objects.filter(estado=True).order_by("nombre").values("id_sede", "nombre")
        )
        tipos = list(
            Tipos_venta.objects.filter(estado=True)
            .order_by("nombre")
            .values("id_tipo_venta", "nombre")
        )
        metodos = list(
            Metodos_pago.objects.filter(estado=True)
            .order_by("nombre")
            .values("id_metodo_pago", "nombre")
        )
        return {"sedes": sedes, "tipos_venta": tipos, "metodos_pago": metodos}

    def buscar_productos(self, q: str, id_sede: int) -> dict[str, Any]:
        qs = Productos.objects.filter(estado=True)
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(codigo_producto__icontains=texto)
                | Q(codigo_barras__icontains=texto)
            )
        items = []
        for p in qs.select_related("id_tipo_producto").order_by("nombre")[:24]:
            stock = None
            if p.inventario_habilitado:
                inv = Inventarios.objects.filter(
                    id_producto_id=p.id_producto, id_sede_id=id_sede
                ).first()
                stock = float(inv.cantidad_actual if inv else 0)
            items.append(
                {
                    "id_producto": p.id_producto,
                    "nombre": p.nombre,
                    "codigo": p.codigo_producto,
                    "codigo_barras": p.codigo_barras or "",
                    "precio_venta": float(p.precio_venta),
                    "iva_porcentaje": float(p.iva_porcentaje or 0),
                    "costo_unitario": float(p.precio_compra or 0),
                    "inventario_habilitado": p.inventario_habilitado,
                    "stock_disponible": stock,
                }
            )
        if texto and not items:
            return {"items": [], "mensaje": msg.MSG_SIN_PRODUCTOS}
        return {"items": items, "mensaje": f"Mostrando {len(items)} productos."}

    def _serie(self, sede: Sedes) -> str:
        base = (sede.ciudad or sede.nombre or "POS")[:3].upper().replace(" ", "")
        return f"POS-{base or 'GEN'}"

    def _jornada_abierta(self, id_sede: int, cuando: date | None = None) -> bool:
        dia = cuando or timezone.localdate()
        return Reportes_diarios.objects.filter(
            id_sede_id=id_sede, fecha=dia, estado="ABIERTO"
        ).exists()

    def _asegurar_jornada(self, ctx: AuthContext, id_sede: int) -> None:
        if self._jornada_abierta(id_sede):
            return
        Reportes_diarios.objects.create(
            id_sede_id=id_sede,
            fecha=timezone.localdate(),
            base_inicial=Decimal("0"),
            estado="ABIERTO",
            id_usuario_apertura_id=ctx.id_usuario,
        )

    def _validar_autorizacion(self, body: dict[str, Any]) -> None:
        email = (body.get("autorizador_email") or "").strip().lower()
        clave = body.get("autorizador_clave") or ""
        if not email or not clave:
            raise ReglaNegocioError(msg.MSG_AUTORIZACION, codigo="AUTORIZACION_REQUERIDA")
        user = Usuarios.objects.filter(email=email, estado=True).select_related("id_rol").first()
        if (
            not user
            or user.id_rol.nombre not in ROLES_AUTORIZADORES
            or not user.check_password(clave)
        ):
            raise ReglaNegocioError(msg.MSG_AUTORIZACION_INVALIDA, codigo="AUTORIZACION_INVALIDA")

    def _parse_lineas(self, lineas_in: list[dict[str, Any]]) -> list[dict[str, Any]]:
        lineas: list[dict[str, Any]] = []
        for ln in lineas_in:
            cantidad = Decimal(str(ln.get("cantidad", 0)))
            if cantidad < 1 or cantidad != cantidad.to_integral_value():
                raise ReglaNegocioError(msg.MSG_CANTIDAD)
            pid = int(ln["id_producto"])
            producto = Productos.objects.get(pk=pid, estado=True)
            bruto = float(producto.precio_venta) * float(cantidad)
            desc_pct = Decimal(str(ln.get("descuento_porcentaje") or 0))
            desc_val = Decimal(str(ln.get("descuento_valor") or 0))
            desc_monto = min(bruto, float(desc_pct) / 100 * bruto + float(desc_val))
            if desc_monto > bruto:
                raise ReglaNegocioError(msg.MSG_DESCUENTO_LINEA)
            lineas.append(
                {
                    "id_producto": pid,
                    "nombre": producto.nombre,
                    "cantidad": cantidad,
                    "precio_unitario": producto.precio_venta,
                    "descuento_porcentaje": desc_pct,
                    "descuento_valor": desc_val,
                    "iva_porcentaje": producto.iva_porcentaje or Decimal("0"),
                    "costo_unitario": producto.precio_compra or Decimal("0"),
                    "inventario_habilitado": producto.inventario_habilitado,
                }
            )
        return calcular_lineas(lineas)

    def _validar_pagos(self, pagos: list[dict[str, Any]], total: Decimal) -> list[dict[str, Any]]:
        if not pagos:
            raise ReglaNegocioError(
                msg.MSG_PAGOS_INFERIORES.format(suma=0, total=total, saldo=total)
            )
        normalizados: list[dict[str, Any]] = []
        saldo = total
        for p in pagos:
            metodo = Metodos_pago.objects.get(pk=int(p["id_metodo_pago"]), estado=True)
            valor = Decimal(str(p.get("valor") or 0))
            if valor <= 0:
                raise ReglaNegocioError("El valor del pago debe ser mayor a 0.")
            referencia = (p.get("referencia") or "").strip()
            if metodo.nombre.lower() == "transferencia":
                if not referencia:
                    raise ReglaNegocioError(msg.MSG_REF_TRANSFERENCIA)
                if valor > saldo:
                    raise ReglaNegocioError(
                        msg.MSG_TRANSFERENCIA_EXCESO.format(
                            monto=valor, saldo=saldo.quantize(Decimal("0.01"))
                        )
                    )
            normalizados.append({"metodo": metodo, "valor": valor, "referencia": referencia})
            saldo = (saldo - valor).quantize(Decimal("0.01"))
        if sum(x["valor"] for x in normalizados) < total:
            suma = sum(x["valor"] for x in normalizados)
            raise ReglaNegocioError(
                msg.MSG_PAGOS_INFERIORES.format(
                    suma=suma.quantize(Decimal("0.01")),
                    total=total.quantize(Decimal("0.01")),
                    saldo=(total - suma).quantize(Decimal("0.01")),
                )
            )
        return normalizados

    def _bajar_stock(
        self, ctx: AuthContext, id_sede: int, id_producto: int, cantidad: Decimal, ref: str
    ) -> None:
        inv, _ = Inventarios.objects.select_for_update().get_or_create(
            id_producto_id=id_producto,
            id_sede_id=id_sede,
            defaults={"cantidad_actual": Decimal("0"), "cantidad_reservada": Decimal("0")},
        )
        if inv.cantidad_actual < cantidad:
            nombre = Productos.objects.get(pk=id_producto).nombre
            raise ReglaNegocioError(msg.MSG_STOCK_EMITIR.format(producto=nombre))
        anterior = inv.cantidad_actual
        nueva = (anterior - cantidad).quantize(Decimal("0.01"))
        inv.cantidad_actual = nueva
        inv.save(update_fields=["cantidad_actual"])
        Movimientos_inventario.objects.create(
            id_inventario=inv,
            tipo_movimiento=TIPO_MOV_VENTA,
            cantidad=cantidad,
            cantidad_anterior=anterior,
            cantidad_nueva=nueva,
            motivo="Venta POS",
            referencia=ref,
            id_usuario_id=ctx.id_usuario,
        )

    def _subir_stock(
        self,
        ctx: AuthContext,
        id_sede: int,
        id_producto: int,
        cantidad: Decimal,
        tipo: str,
        ref: str,
    ) -> None:
        inv, _ = Inventarios.objects.select_for_update().get_or_create(
            id_producto_id=id_producto,
            id_sede_id=id_sede,
            defaults={"cantidad_actual": Decimal("0"), "cantidad_reservada": Decimal("0")},
        )
        anterior = inv.cantidad_actual
        nueva = (anterior + cantidad).quantize(Decimal("0.01"))
        inv.cantidad_actual = nueva
        inv.save(update_fields=["cantidad_actual"])
        Movimientos_inventario.objects.create(
            id_inventario=inv,
            tipo_movimiento=tipo,
            cantidad=cantidad,
            cantidad_anterior=anterior,
            cantidad_nueva=nueva,
            motivo="Reversión inventario por factura",
            referencia=ref,
            id_usuario_id=ctx.id_usuario,
        )

    def _consecutivo(self, sede: Sedes) -> tuple[str, str]:
        serie = self._serie(sede)
        row, _ = Consecutivos.objects.select_for_update().get_or_create(
            id_sede_id=sede.id_sede,
            serie=serie,
            defaults={"ultimo_numero": 0, "version": 1},
        )
        row.ultimo_numero += 1
        row.save(update_fields=["ultimo_numero"])
        numero = str(row.ultimo_numero).zfill(10)
        return serie, numero

    def _factura_dict(self, f: Facturas, detalle: bool = False) -> dict[str, Any]:
        consecutivo = f"{f.serie}-{f.numero_factura}"
        fe = Facturas_electronicas.objects.filter(id_factura_id=f.id_factura).first()
        data: dict[str, Any] = {
            "id_factura": f.id_factura,
            "consecutivo": consecutivo,
            "serie": f.serie,
            "numero_factura": f.numero_factura,
            "estado": f.estado,
            "fecha_hora": f.fecha_hora.isoformat(),
            "id_sede": f.id_sede_id,
            "sede": f.id_sede.nombre,
            "id_tipo_venta": f.id_tipo_venta_id,
            "tipo_venta": f.id_tipo_venta.nombre,
            "id_cliente": f.id_cliente_id,
            "cliente": (
                f"{f.id_cliente.nombre} {f.id_cliente.apellido or ''}".strip()
                if f.id_cliente_id and f.id_cliente
                else f.comprador_nombre or "Consumidor final"
            ),
            "id_usuario": f.id_usuario_id,
            "empleado": f"{f.id_usuario.nombre} {f.id_usuario.apellido}".strip(),
            "subtotal": float(f.subtotal),
            "descuento": float(f.descuento),
            "impuesto": float(f.impuesto),
            "total": float(f.total),
            "margen_negativo": f.margen_negativo,
            "requiere_revision_gerencial": f.requiere_revision_gerencial,
            "requiere_factura_electronica": f.requiere_factura_electronica,
            "factura_electronica_estado": fe.estado if fe else None,
            "observaciones": f.observaciones,
            "version_fila": f.version_fila,
        }
        if not detalle:
            return data
        data["lineas"] = [
            {
                "id_detalle": d.id_detalle,
                "id_producto": d.id_producto_id,
                "producto": d.id_producto.nombre,
                "cantidad": float(d.cantidad),
                "cantidad_devuelta": float(d.cantidad_devuelta),
                "precio_unitario": float(d.precio_unitario),
                "subtotal": float(d.subtotal),
                "descuento_porcentaje": float(d.descuento_porcentaje),
                "descuento_valor": float(d.descuento_valor),
            }
            for d in f.detalles.select_related("id_producto").all()
        ]
        data["pagos"] = [
            {
                "id_pago": p.id_pago,
                "metodo": p.id_metodo_pago.nombre,
                "valor": float(p.valor),
                "referencia": p.referencia,
            }
            for p in f.pagos.select_related("id_metodo_pago").all()
        ]
        data["descuentos"] = list(
            f.descuentos.values("tipo_descuento", "porcentaje", "valor", "motivo")
        )
        return data

    def emitir(self, ctx: AuthContext, body: dict[str, Any]) -> dict[str, Any]:
        from apps.m06_ventas.admin_ventas_emitir import emitir_factura

        return emitir_factura(self, ctx, body)

    def listar(
        self, ctx: AuthContext, filtros: dict[str, str], page: int, page_size: int
    ) -> dict[str, Any]:
        from apps.m06_ventas.admin_ventas_emitir import listar_facturas

        return listar_facturas(self, ctx, filtros, page, page_size)

    def obtener(self, ctx: AuthContext, pk: int) -> dict[str, Any]:
        from apps.m06_ventas.admin_ventas_emitir import obtener_factura

        return obtener_factura(self, ctx, pk)

    def anular(self, ctx: AuthContext, pk: int, body: dict[str, Any]) -> dict[str, Any]:
        from apps.m06_ventas.admin_ventas_emitir import anular_factura

        return anular_factura(self, ctx, pk, body)

    def devolucion(self, ctx: AuthContext, pk: int, body: dict[str, Any]) -> dict[str, Any]:
        from apps.m06_ventas.admin_ventas_emitir import devolucion_parcial

        return devolucion_parcial(self, ctx, pk, body)

    def editar(self, ctx: AuthContext, pk: int, body: dict[str, Any]) -> dict[str, Any]:
        from apps.m06_ventas.admin_ventas_emitir import editar_factura

        return editar_factura(self, ctx, pk, body)
