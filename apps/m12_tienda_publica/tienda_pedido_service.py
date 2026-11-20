"""Validación de carrito y pedido WhatsApp (HU 90–92)."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Productos
from apps.m04_inventario.models import Inventarios
from apps.m12_tienda_publica import mensajes as msg
from apps.m12_tienda_publica.models import Pedidos_web
from apps.m12_tienda_publica.slug_util import ruta_producto
from contratos.excepciones import ReglaNegocioError

E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")
MAX_CANTIDAD = 99


def _stock(id_producto: int, id_sede: int | None) -> Decimal:
    qs = Inventarios.objects.filter(id_producto_id=id_producto)
    if id_sede:
        qs = qs.filter(id_sede_id=id_sede)
    return Decimal(str(qs.aggregate(t=Coalesce(Sum("cantidad_actual"), Decimal("0")))["t"] or 0))


def _linea_disponible(prod: Productos, cantidad: Decimal, id_sede: int | None) -> bool:
    if not prod.estado:
        return False
    if not prod.inventario_habilitado:
        return True
    return _stock(prod.id_producto, id_sede) >= cantidad


class TiendaPedidoService:
    def validar_carrito(self, id_sede: int | None, items_in: list[dict[str, Any]]) -> dict[str, Any]:
        lineas: list[dict[str, Any]] = []
        mensajes: list[str] = []
        hubo_cambios = False
        total = Decimal("0")

        for raw in items_in:
            try:
                pid = int(raw.get("id_producto") or 0)
                cantidad = int(raw.get("cantidad") or 0)
            except (TypeError, ValueError) as exc:
                raise ReglaNegocioError(msg.MSG_CANTIDAD, codigo="VALIDACION") from exc
            if cantidad < 1:
                raise ReglaNegocioError(msg.MSG_CANTIDAD, codigo="VALIDACION")

            prod = Productos.objects.filter(pk=pid, estado=True).first()
            if not prod:
                mensajes.append(msg.MSG_PRODUCTO_RETIRADO.format(producto=f"ID {pid}"))
                hubo_cambios = True
                continue

            precio_servidor = prod.precio_venta
            precio_cliente = raw.get("precio_cliente")
            if precio_cliente is not None:
                try:
                    if Decimal(str(precio_cliente)) != precio_servidor:
                        mensajes.append(
                            msg.MSG_PRECIO_CAMBIO.format(
                                producto=prod.nombre,
                                anterior=str(precio_cliente),
                                nuevo=str(precio_servidor),
                            )
                        )
                        hubo_cambios = True
                except (InvalidOperation, TypeError):
                    hubo_cambios = True

            limite = MAX_CANTIDAD
            if prod.inventario_habilitado:
                disp = int(_stock(prod.id_producto, id_sede))
                limite = min(MAX_CANTIDAD, max(1, disp)) if disp > 0 else 0
            if not _linea_disponible(prod, Decimal(cantidad), id_sede):
                mensajes.append(msg.MSG_PRODUCTO_RETIRADO.format(producto=prod.nombre))
                hubo_cambios = True
                continue
            if cantidad > limite:
                mensajes.append(msg.MSG_CANTIDAD_LIMITE)
                cantidad = limite
                hubo_cambios = True

            subtotal = precio_servidor * cantidad
            total += subtotal
            lineas.append(
                {
                    "id_producto": prod.id_producto,
                    "nombre": prod.nombre,
                    "slug": ruta_producto(prod.id_producto, prod.nombre),
                    "codigo_producto": prod.codigo_producto,
                    "cantidad": cantidad,
                    "precio_unitario": str(precio_servidor),
                    "subtotal": str(subtotal),
                    "agotado": False,
                }
            )

        if not lineas:
            raise ReglaNegocioError(msg.MSG_CARRITO_VALIDAR_FALLA, codigo="CARRITO_VACIO")

        mensaje = msg.MSG_CARRITO_VALIDADO if not hubo_cambios else "\n".join(mensajes)
        return {
            "mensaje": mensaje,
            "hubo_cambios": hubo_cambios,
            "items": lineas,
            "total": str(total),
        }

    def sedes_activas(self) -> dict[str, Any]:
        items = [
            {
                "id_sede": s.id_sede,
                "nombre": s.nombre,
                "direccion": s.direccion,
                "whatsapp": (s.whatsapp or "").strip(),
            }
            for s in Sedes.objects.filter(estado=True).order_by("nombre")
            if (s.whatsapp or "").strip()
        ]
        return {"items": items}

    def contacto_whatsapp(self, id_sede: int | None, texto: str | None) -> dict[str, Any]:
        numero = ""
        if id_sede:
            sede = Sedes.objects.filter(pk=id_sede, estado=True).first()
            if sede:
                numero = (sede.whatsapp or "").strip()
        if not numero:
            numero = msg.DEFAULT_WHATSAPP
        digits = re.sub(r"\D", "", numero)
        if not digits:
            raise ReglaNegocioError(msg.MSG_WHATSAPP_NO, codigo="SIN_NUMERO")
        msg_text = (texto or "¡Hola! Deseo recibir información o atención de un asesor.").strip()
        url = f"https://wa.me/{digits}?text={quote(msg_text)}"
        if len(url) > msg.WHATSAPP_URL_MAX:
            raise ReglaNegocioError(msg.MSG_PEDIDO_LARGO, codigo="URL_LARGA")
        return {"url_whatsapp": url}

    @transaction.atomic
    def preparar_pedido(self, datos: dict[str, Any]) -> dict[str, Any]:
        nombre = (datos.get("cliente_nombre") or datos.get("nombre_contacto") or "").strip()
        telefono = (datos.get("cliente_telefono") or datos.get("telefono_contacto") or "").strip()
        id_sede = int(datos.get("id_sede") or 0)
        items_in = datos.get("items") or []
        if not nombre:
            raise ReglaNegocioError(msg.MSG_PEDIDO_FALLA, codigo="VALIDACION")
        if not E164_RE.match(telefono):
            raise ReglaNegocioError(msg.MSG_TELEFONO, codigo="TELEFONO_INVALIDO")
        if not id_sede:
            raise ReglaNegocioError(msg.MSG_SEDE_REQUERIDA, codigo="VALIDACION")

        sede = Sedes.objects.filter(pk=id_sede, estado=True).first()
        if not sede:
            raise ReglaNegocioError(msg.MSG_SEDE_REQUERIDA, codigo="SEDE_INVALIDA")
        wa = (sede.whatsapp or "").strip()
        if not wa:
            raise ReglaNegocioError(msg.MSG_SEDE_SIN_WHATSAPP, codigo="SIN_WHATSAPP")

        validado = self.validar_carrito(id_sede, items_in)
        lineas = validado["items"]
        total = Decimal(validado["total"])

        cuerpo = [
            f"Pedido web — {sede.nombre}",
            f"Cliente: {nombre}",
            f"Tel: {telefono}",
        ]
        dir_ent = (datos.get("direccion_entrega") or "").strip()
        obs = (datos.get("observaciones") or "").strip()
        if dir_ent:
            cuerpo.append(f"Dirección: {dir_ent}")
        if obs:
            cuerpo.append(f"Notas: {obs}")
        cuerpo.append("—")
        for ln in lineas:
            cuerpo.append(f"{ln['cantidad']}× {ln['nombre']} ({ln['codigo_producto']}) = ${ln['subtotal']}")
        cuerpo.append(f"Total: ${total}")
        texto = "\n".join(cuerpo)

        digits = re.sub(r"\D", "", wa)
        url = f"https://wa.me/{digits}?text={quote(texto)}"
        if len(url) > msg.WHATSAPP_URL_MAX:
            raise ReglaNegocioError(msg.MSG_PEDIDO_LARGO, codigo="URL_LARGA")

        clave = (datos.get("clave_idempotencia") or str(uuid.uuid4())).strip()[:128]
        if Pedidos_web.objects.filter(clave_idempotencia=clave).exists():
            existente = Pedidos_web.objects.get(clave_idempotencia=clave)
            return {
                "mensaje": msg.MSG_PEDIDO_LISTO,
                "url_whatsapp": url,
                "id_pedido_web": existente.id_pedido_web,
            }

        pedido = Pedidos_web.objects.create(
            clave_idempotencia=clave,
            nombre_contacto=nombre[:255],
            telefono_contacto=telefono[:20],
            direccion_entrega=dir_ent[:500],
            observaciones=obs,
            id_sede=sede,
            items_json=lineas,
            total_estimado=total,
            estado="PENDIENTE",
        )
        return {
            "mensaje": msg.MSG_PEDIDO_LISTO,
            "url_whatsapp": url,
            "id_pedido_web": pedido.id_pedido_web,
        }
