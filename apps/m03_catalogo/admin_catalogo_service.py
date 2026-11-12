"""Backoffice de catálogo (HU 22–30)."""

from __future__ import annotations

import csv
import io
import logging
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from PIL import Image

from apps.m01_identidad.models import Usuarios
from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.mensajes import (
    MSG_ACTUALIZADO,
    MSG_ACTUALIZADO_PRECIO,
    MSG_ACTUALIZAR_ERROR,
    MSG_ARCHIVO,
    MSG_BARRAS_DUP,
    MSG_BARRAS_INVALIDO,
    MSG_CODIGO_DUP,
    MSG_CODIGO_INVALIDO,
    MSG_CONCURRENCIA,
    MSG_CREADO,
    MSG_CREAR_ERROR,
    MSG_ESTADO_ERROR,
    MSG_ESTADO_OK,
    MSG_EXPORT_ERROR,
    MSG_EXPORT_VACIO,
    MSG_FECHAS,
    MSG_HISTORIAL,
    MSG_HISTORIAL_VACIO,
    MSG_IMPORT_ERROR,
    MSG_IMPORT_EXISTE,
    MSG_IMPORT_FORMATO,
    MSG_IMPORT_LIMITE,
    MSG_IMPORT_OK,
    MSG_LISTADO,
    MSG_MOTIVO_PRECIO,
    MSG_NOMBRE_DUP,
    MSG_NOMBRE_OBL,
    MSG_OBLIGATORIOS,
    MSG_PARAM_CREADO,
    MSG_PARAM_EDITAR_ERROR,
    MSG_PARAM_ELIMINADO,
    MSG_PARAM_ELIMINAR_ERROR,
    MSG_PARAM_GUARDAR_ERROR,
    MSG_PARAM_OK,
    MSG_PARAMETRO_INACTIVO,
    MSG_RANGO_INVALIDO,
    MSG_SIN_COINCIDENCIAS,
    MSG_TIPO_BASE,
    MSG_UNIDAD_INVALIDA,
)
from apps.m03_catalogo.models import (
    Categorias_producto,
    Historial_precios,
    Marcas,
    Productos,
    Tipos_producto,
)
from apps.m04_inventario.models import Inventarios
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import DominioError, ReglaNegocioError

logger = logging.getLogger(__name__)

UNIDADES = ("UND", "KG", "GR", "LT", "ML", "MT", "CJ", "PQT")
COLUMNAS_IMPORT = [
    "codigo_producto",
    "codigo_barras",
    "nombre",
    "descripcion",
    "categoria",
    "marca",
    "tipo_producto",
    "unidad_medida",
    "precio_compra",
    "precio_venta",
    "iva_porcentaje",
    "stock_minimo",
    "inventario_habilitado",
    "origen",
]
MAX_IMAGEN = 5 * 1024 * 1024
MAX_IMPORT = 10 * 1024 * 1024
MIME_OK = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
ORIGEN_ETIQUETA = dict(Productos.ORIGEN_CHOICES)


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):  # pragma: no cover
        raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS") from None


def _usuario_id(ctx: AuthContext) -> int | None:
    if not ctx.id_usuario:  # pragma: no cover
        return None
    return ctx.id_usuario if Usuarios.objects.filter(pk=ctx.id_usuario).exists() else None


def _audit(ctx: AuthContext, accion: str, entidad: str, id_entidad: int, antes, despues) -> None:
    AuditService().registrar(
        AuditoriaDTO(
            id_usuario=_usuario_id(ctx),
            accion=accion,
            entidad=entidad,
            id_entidad=id_entidad,
            datos_antes=antes,
            datos_despues=despues,
            motivo=accion,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


def _snap(p: Productos) -> dict[str, Any]:
    return {
        "id_producto": p.id_producto,
        "codigo_producto": p.codigo_producto,
        "codigo_barras": p.codigo_barras or "",
        "nombre": p.nombre,
        "precio_compra": str(p.precio_compra),
        "precio_venta": str(p.precio_venta),
        "iva_porcentaje": str(p.iva_porcentaje),
        "estado": p.estado,
        "origen": p.origen,
        "version_fila": p.version,
    }


class AdminCatalogoService:
    def listar(self, q: str, filtros: dict[str, str], page: int, page_size: int, orden: str) -> dict[str, Any]:
        qs = Productos.objects.select_related("id_categoria", "id_marca", "id_tipo_producto")
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(codigo_producto__icontains=texto)
                | Q(codigo_barras__icontains=texto)
                | Q(id_marca__nombre__icontains=texto)
            )
        if filtros.get("id_categoria"):
            qs = qs.filter(id_categoria_id=int(filtros["id_categoria"]))
        if filtros.get("id_marca"):
            qs = qs.filter(id_marca_id=int(filtros["id_marca"]))
        if filtros.get("id_tipo"):
            qs = qs.filter(id_tipo_producto_id=int(filtros["id_tipo"]))
        estado = (filtros.get("estado") or "todos").lower()
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)
        stock = (filtros.get("stock") or "todos").lower()
        ids = list(qs.values_list("id_producto", flat=True)[:5000])
        existencias = {
            row["id_producto"]: row["total"] or Decimal("0")
            for row in Inventarios.objects.filter(id_producto_id__in=ids, id_sede__estado=True)
            .values("id_producto")
            .annotate(total=Sum("cantidad_actual"))
        }
        items_src = list(qs.order_by("nombre")[:5000])
        filas = []
        for p in items_src:
            total = existencias.get(p.id_producto, Decimal("0"))
            if not p.inventario_habilitado:
                nivel = "na"
            elif total == 0:
                nivel = "agotado"
            elif total <= p.stock_minimo:
                nivel = "bajo"
            else:
                nivel = "ok"
            if stock == "con_stock" and nivel != "ok":
                continue
            if stock == "bajo" and nivel != "bajo":
                continue
            if stock == "agotado" and nivel != "agotado":
                continue
            filas.append((p, total, nivel))
        campos = {
            "codigo": lambda r: r[0].codigo_producto,
            "nombre": lambda r: r[0].nombre.lower(),
            "categoria": lambda r: (r[0].id_categoria.nombre if r[0].id_categoria else "").lower(),
            "marca": lambda r: (r[0].id_marca.nombre if r[0].id_marca else "").lower(),
            "tipo": lambda r: (r[0].id_tipo_producto.nombre if r[0].id_tipo_producto else "").lower(),
            "precio": lambda r: r[0].precio_venta,
            "existencia": lambda r: r[1],
            "estado": lambda r: r[0].estado,
        }
        clave = (orden or "nombre").lstrip("-")
        reverse = (orden or "").startswith("-")
        filas.sort(key=campos.get(clave, campos["nombre"]), reverse=reverse)
        total = len(filas)
        offset = max(0, (page - 1) * page_size)
        page_rows = filas[offset : offset + page_size]
        items = [
            {
                "id_producto": p.id_producto,
                "codigo_producto": p.codigo_producto,
                "nombre": p.nombre,
                "categoria": p.id_categoria.nombre if p.id_categoria else "",
                "marca": p.id_marca.nombre if p.id_marca else "",
                "tipo": p.id_tipo_producto.nombre if p.id_tipo_producto else "",
                "precio_compra": str(p.precio_compra),
                "precio_venta": str(p.precio_venta),
                "iva_porcentaje": str(p.iva_porcentaje),
                "unidad_medida": p.unidad_medida,
                "existencia": None if not p.inventario_habilitado else str(total_ex),
                "stock_nivel": nivel,
                "estado": p.estado,
                "imagen_url": p.imagen_url,
                "origen": p.origen,
                "version_fila": p.version,
            }
            for p, total_ex, nivel in page_rows
        ]
        mensaje = MSG_SIN_COINCIDENCIAS if total == 0 else MSG_LISTADO.format(n=len(items), total=total)
        return {"items": items, "total": total, "page": page, "page_size": page_size, "mensaje": mensaje}

    def detalle(self, id_producto: int) -> dict[str, Any]:
        p = Productos.objects.select_related("id_categoria", "id_marca", "id_tipo_producto").get(pk=id_producto)
        data = _snap(p)
        data.update(
            {
                "descripcion": p.descripcion,
                "id_categoria": p.id_categoria_id if p.id_categoria_id else None,
                "id_marca": p.id_marca_id,
                "id_tipo_producto": p.id_tipo_producto_id,
                "unidad_medida": p.unidad_medida,
                "stock_minimo": p.stock_minimo,
                "inventario_habilitado": p.inventario_habilitado,
                "imagen_url": p.imagen_url,
            }
        )
        return data

    def _validar_comun(self, datos: dict[str, Any], propio: int | None = None) -> dict[str, Any]:
        codigo = str(datos.get("codigo_producto") or "").strip()
        nombre = str(datos.get("nombre") or "").strip()
        unidad = str(datos.get("unidad_medida") or "").strip().upper()
        barras = str(datos.get("codigo_barras") or "").strip()
        oblig = [codigo, nombre, datos.get("id_categoria"), datos.get("id_marca"), datos.get("id_tipo_producto"), unidad]
        if any(v in (None, "") for v in oblig) or datos.get("precio_compra") in (None, "") or datos.get("precio_venta") in (None, "") or datos.get("iva_porcentaje") in (None, "") or datos.get("stock_minimo") in (None, ""):
            raise ReglaNegocioError(MSG_OBLIGATORIOS, codigo="CAMPOS_OBLIGATORIOS")
        if len(codigo) > 30 or not codigo.replace("-", "").replace("_", "").isalnum():
            raise ReglaNegocioError(MSG_CODIGO_INVALIDO, codigo="CODIGO_INVALIDO")
        if len(nombre) > 255:
            raise ReglaNegocioError(MSG_CODIGO_INVALIDO, codigo="NOMBRE_LARGO")
        if unidad not in UNIDADES:
            raise ReglaNegocioError(MSG_UNIDAD_INVALIDA, codigo="UNIDAD_INVALIDA")
        if barras and (not barras.isdigit() or len(barras) > 14):
            raise ReglaNegocioError(MSG_BARRAS_INVALIDO, codigo="BARRAS_INVALIDO")
        compra = _d(datos.get("precio_compra"))
        venta = _d(datos.get("precio_venta"))
        iva = _d(datos.get("iva_porcentaje"))
        try:
            stock = int(str(datos.get("stock_minimo")))
        except (TypeError, ValueError):
            raise ReglaNegocioError(MSG_RANGO_INVALIDO, codigo="STOCK_INVALIDO") from None
        if compra < 0 or venta < 0 or iva < 0 or iva > 100 or stock < 0:
            raise ReglaNegocioError(MSG_RANGO_INVALIDO, codigo="RANGO_INVALIDO")
        origen = str(datos.get("origen") or Productos.ORIGEN_COMPRADO).strip().lower()
        if origen not in {Productos.ORIGEN_COMPRADO, Productos.ORIGEN_FABRICADO}:
            raise ReglaNegocioError(MSG_RANGO_INVALIDO, codigo="ORIGEN_INVALIDO")
        dup = Productos.objects.filter(codigo_producto__iexact=codigo)
        if propio:
            dup = dup.exclude(pk=propio)
        if dup.exists():
            raise ReglaNegocioError(MSG_CODIGO_DUP, codigo="CODIGO_DUPLICADO")
        if barras:
            dupb = Productos.objects.filter(codigo_barras=barras)
            if propio:
                dupb = dupb.exclude(pk=propio)
            if dupb.exists():
                raise ReglaNegocioError(MSG_BARRAS_DUP, codigo="BARRAS_DUPLICADO")
        for modelo, _campo, pk in (
            (Categorias_producto, "id_categoria", int(str(datos["id_categoria"]))),
            (Marcas, "id_marca", int(str(datos["id_marca"]))),
            (Tipos_producto, "id_tipo_producto", int(str(datos["id_tipo_producto"]))),
        ):
            if not modelo.objects.filter(pk=pk, estado=True).exists():
                raise ReglaNegocioError(MSG_PARAMETRO_INACTIVO, codigo="PARAMETRO_INACTIVO")
        return {
            "codigo_producto": codigo,
            "codigo_barras": barras or None,
            "nombre": nombre,
            "descripcion": str(datos.get("descripcion") or "").strip(),
            "id_categoria_id": int(str(datos["id_categoria"])),
            "id_marca_id": int(str(datos["id_marca"])),
            "id_tipo_producto_id": int(str(datos["id_tipo_producto"])),
            "unidad_medida": unidad,
            "precio_compra": compra,
            "precio_venta": venta,
            "iva_porcentaje": iva,
            "stock_minimo": stock,
            "inventario_habilitado": bool(datos.get("inventario_habilitado", True)),
            "origen": origen,
            "advertencia_precio": venta < compra,
        }

    def crear(self, ctx: AuthContext, datos: dict[str, Any]) -> tuple[dict[str, Any], str]:
        limpio = self._validar_comun(datos)
        aviso = limpio.pop("advertencia_precio")
        try:
            with transaction.atomic():
                ahora = timezone.now()
                producto = Productos.objects.create(**limpio, estado=True, version=1)
                Historial_precios.objects.create(
                    id_producto=producto,
                    precio_anterior=Decimal("0.00"),
                    precio_nuevo=producto.precio_venta,
                    precio_compra=producto.precio_compra,
                    iva_porcentaje=producto.iva_porcentaje,
                    fecha_inicio=ahora,
                    motivo="Vigencia inicial",
                    id_usuario_id=_usuario_id(ctx),
                )
                if producto.inventario_habilitado:
                    for sede in Sedes.objects.filter(estado=True).only("id_sede"):
                        Inventarios.objects.get_or_create(
                            id_producto=producto,
                            id_sede=sede,
                            defaults={"cantidad_actual": 0, "cantidad_reservada": 0},
                        )
                _audit(ctx, "CREAR_PRODUCTO", "Productos", producto.id_producto, None, _snap(producto))
            body = self.detalle(producto.id_producto)
            body["advertencia_precio"] = aviso
            return body, MSG_CREADO
        except ReglaNegocioError:
            raise
        except Exception:  # pragma: no cover
            logger.exception("crear_producto")
            raise DominioError(MSG_CREAR_ERROR, codigo="PRODUCTO_CREAR_ERROR") from None

    def editar(self, ctx: AuthContext, id_producto: int, datos: dict[str, Any]) -> tuple[dict[str, Any], str]:
        limpio = self._validar_comun(datos, propio=id_producto)
        limpio.pop("advertencia_precio")
        motivo = str(datos.get("motivo") or "").strip()
        try:
            version = int(datos.get("version_fila") or 0)
        except (TypeError, ValueError):
            version = 0
        try:
            with transaction.atomic():
                producto = Productos.objects.select_for_update().get(pk=id_producto)
                if producto.version != version:
                    raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
                precio_cambio = (
                    producto.precio_compra != limpio["precio_compra"]
                    or producto.precio_venta != limpio["precio_venta"]
                    or producto.iva_porcentaje != limpio["iva_porcentaje"]
                )
                if precio_cambio and not motivo:
                    raise ReglaNegocioError(MSG_MOTIVO_PRECIO, codigo="MOTIVO_PRECIO")
                if precio_cambio and len(motivo) > 255:
                    raise ReglaNegocioError(MSG_MOTIVO_PRECIO, codigo="MOTIVO_LARGO")
                antes = _snap(producto)
                for k, v in limpio.items():
                    setattr(producto, k, v)
                producto.version = int(producto.version) + 1
                producto.save()
                mensaje = MSG_ACTUALIZADO
                if precio_cambio:
                    ahora = timezone.now()
                    Historial_precios.objects.filter(id_producto=producto, fecha_fin__isnull=True).update(fecha_fin=ahora)
                    Historial_precios.objects.create(
                        id_producto=producto,
                        precio_anterior=Decimal(antes["precio_venta"]),
                        precio_nuevo=producto.precio_venta,
                        precio_compra=producto.precio_compra,
                        iva_porcentaje=producto.iva_porcentaje,
                        fecha_inicio=ahora,
                        motivo=motivo,
                        id_usuario_id=_usuario_id(ctx),
                    )
                    mensaje = MSG_ACTUALIZADO_PRECIO
                _audit(ctx, "EDITAR_PRODUCTO", "Productos", producto.id_producto, antes, _snap(producto))
            return self.detalle(producto.id_producto), mensaje
        except (ReglaNegocioError, Productos.DoesNotExist):
            raise
        except Exception:  # pragma: no cover
            logger.exception("editar_producto")
            raise DominioError(MSG_ACTUALIZAR_ERROR, codigo="PRODUCTO_EDITAR_ERROR") from None

    def cambiar_estado(self, ctx: AuthContext, id_producto: int, activo: bool) -> str:
        try:
            with transaction.atomic():
                producto = Productos.objects.select_for_update().get(pk=id_producto)
                antes = _snap(producto)
                producto.estado = activo
                producto.version = int(producto.version) + 1
                producto.save(update_fields=["estado", "version"])
                _audit(ctx, "CAMBIAR_ESTADO_PRODUCTO", "Productos", producto.id_producto, antes, _snap(producto))
            return MSG_ESTADO_OK
        except Productos.DoesNotExist:
            raise
        except Exception:  # pragma: no cover
            logger.exception("estado_producto")
            raise DominioError(MSG_ESTADO_ERROR, codigo="PRODUCTO_ESTADO_ERROR") from None

    def historial(self, id_producto: int, desde: str, hasta: str) -> dict[str, Any]:
        if not Productos.objects.filter(pk=id_producto).exists():
            raise Productos.DoesNotExist
        qs = Historial_precios.objects.filter(id_producto_id=id_producto).select_related("id_usuario").order_by("-fecha_cambio")
        if desde and hasta and desde > hasta:
            raise ReglaNegocioError(MSG_FECHAS, codigo="RANGO_FECHAS")
        if desde:
            qs = qs.filter(fecha_cambio__date__gte=desde)
        if hasta:
            qs = qs.filter(fecha_cambio__date__lte=hasta)
        filas = list(qs[:500])
        items = []
        previo = None
        for h in filas:
            usuario = ""
            if h.id_usuario_id and h.id_usuario:
                usuario = f"{h.id_usuario.nombre} {h.id_usuario.apellido}".strip()
            items.append(
                {
                    "id_historial": h.id_historial,
                    "precio_compra": str(h.precio_compra if h.precio_compra is not None else ""),
                    "precio_venta": str(h.precio_nuevo),
                    "iva_porcentaje": str(h.iva_porcentaje if h.iva_porcentaje is not None else ""),
                    "fecha_inicio": (h.fecha_inicio or h.fecha_cambio).isoformat(),
                    "fecha_fin": h.fecha_fin.isoformat() if h.fecha_fin else "",
                    "motivo": h.motivo,
                    "usuario": usuario,
                    "precio_anterior": str(h.precio_anterior),
                    "precio_nuevo": str(h.precio_nuevo),
                }
            )
            previo = h
        del previo
        mensaje = MSG_HISTORIAL_VACIO if not items else MSG_HISTORIAL.format(n=len(items))
        producto = Productos.objects.get(pk=id_producto)
        return {
            "producto": {"codigo_producto": producto.codigo_producto, "nombre": producto.nombre},
            "items": items,
            "mensaje": mensaje,
        }

    def guardar_imagen(self, id_producto: int, nombre: str, contenido: bytes, mime: str) -> str:
        if mime not in MIME_OK or len(contenido) > MAX_IMAGEN or len(contenido) == 0:
            raise ReglaNegocioError(MSG_ARCHIVO, codigo="ARCHIVO_INVALIDO")
        try:
            imagen = Image.open(io.BytesIO(contenido))
            imagen.verify()
            rgb = Image.open(io.BytesIO(contenido)).convert("RGB")
        except Exception:  # pragma: no cover
            raise ReglaNegocioError(MSG_ARCHIVO, codigo="ARCHIVO_INVALIDO") from None
        base = Path(settings.BASE_DIR) / "media" / "productos"
        base.mkdir(parents=True, exist_ok=True)
        stem = f"{id_producto}-{uuid.uuid4().hex[:8]}"
        principal = base / f"{stem}.webp"
        thumb = base / f"{stem}_thumb.webp"
        rgb.save(principal, format="WEBP", quality=82)
        rgb.thumbnail((160, 160))
        rgb.save(thumb, format="WEBP", quality=75)
        rel = f"productos/{principal.name}"
        Productos.objects.filter(pk=id_producto).update(imagen_url=rel)
        return rel

    def catalogos_activos(self) -> dict[str, Any]:
        return {
            "categorias": list(Categorias_producto.objects.filter(estado=True).order_by("nombre").values("id_categoria", "nombre")),
            "marcas": list(Marcas.objects.filter(estado=True).order_by("nombre").values("id_marca", "nombre")),
            "tipos": list(Tipos_producto.objects.filter(estado=True).order_by("nombre").values("id_tipo_producto", "nombre", "es_base")),
            "unidades": list(UNIDADES),
        }

    def listar_param(self, tipo: str) -> list[dict[str, Any]]:
        modelo: Any = {"categorias": Categorias_producto, "marcas": Marcas, "tipos": Tipos_producto}[tipo]
        pk = {"categorias": "id_categoria", "marcas": "id_marca", "tipos": "id_tipo_producto"}[tipo]
        items = []
        for row in modelo.objects.all().order_by("nombre"):
            item = {"id": getattr(row, pk), "nombre": row.nombre, "descripcion": row.descripcion, "estado": row.estado, "version_fila": row.version_fila}
            if tipo == "tipos":
                item["afecta_venta_diaria"] = row.afecta_venta_diaria
                item["es_base"] = row.es_base
            items.append(item)
        return items

    def crear_param(self, ctx: AuthContext, tipo: str, datos: dict[str, Any]) -> str:
        nombre = str(datos.get("nombre") or "").strip()
        if not nombre:
            raise ReglaNegocioError(MSG_NOMBRE_OBL, codigo="NOMBRE_OBLIGATORIO")
        if len(nombre) > 255:
            raise ReglaNegocioError(MSG_NOMBRE_OBL, codigo="NOMBRE_LARGO")
        modelo: Any = {"categorias": Categorias_producto, "marcas": Marcas, "tipos": Tipos_producto}[tipo]
        if modelo.objects.filter(nombre__iexact=nombre).exists():
            raise ReglaNegocioError(MSG_NOMBRE_DUP, codigo="NOMBRE_DUPLICADO")
        etiqueta = {"categorias": "Categoría", "marcas": "Marca", "tipos": "Tipo"}[tipo]
        try:
            with transaction.atomic():
                kwargs: dict[str, Any] = {"nombre": nombre, "descripcion": str(datos.get("descripcion") or "").strip(), "estado": True}
                if tipo == "tipos":
                    kwargs["afecta_venta_diaria"] = bool(datos.get("afecta_venta_diaria", True))
                    kwargs["es_base"] = False
                row = modelo.objects.create(**kwargs)
                _audit(ctx, "CREAR_PARAMETRO", modelo.__name__, row.pk, None, {"nombre": nombre})
            return MSG_PARAM_CREADO.format(tipo=etiqueta)
        except ReglaNegocioError:
            raise
        except Exception:  # pragma: no cover
            logger.exception("crear_param")
            raise DominioError(MSG_PARAM_GUARDAR_ERROR, codigo="PARAM_GUARDAR_ERROR") from None

    def editar_param(self, ctx: AuthContext, tipo: str, id_row: int, datos: dict[str, Any]) -> str:
        modelo: Any = {"categorias": Categorias_producto, "marcas": Marcas, "tipos": Tipos_producto}[tipo]
        nombre = str(datos.get("nombre") or "").strip()
        if not nombre:
            raise ReglaNegocioError(MSG_NOMBRE_OBL, codigo="NOMBRE_OBLIGATORIO")
        try:
            with transaction.atomic():
                row = modelo.objects.select_for_update().get(pk=id_row)
                if int(datos.get("version_fila") or 0) != row.version_fila:
                    raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
                nuevo_estado = bool(datos.get("estado", True))
                if tipo == "tipos" and getattr(row, "es_base", False) and not nuevo_estado:
                    raise ReglaNegocioError(MSG_TIPO_BASE, codigo="TIPO_BASE")
                if modelo.objects.filter(nombre__iexact=nombre).exclude(pk=id_row).exists():
                    raise ReglaNegocioError(MSG_NOMBRE_DUP, codigo="NOMBRE_DUPLICADO")
                antes = {"nombre": row.nombre, "estado": row.estado}
                row.nombre = nombre
                row.descripcion = str(datos.get("descripcion") or "").strip()
                row.estado = nuevo_estado
                if tipo == "tipos" and not row.es_base:
                    row.afecta_venta_diaria = bool(datos.get("afecta_venta_diaria", row.afecta_venta_diaria))
                row.version_fila = int(row.version_fila) + 1
                row.save()
                _audit(ctx, "EDITAR_PARAMETRO", modelo.__name__, row.pk, antes, {"nombre": row.nombre, "estado": row.estado})
            return MSG_PARAM_OK
        except (ReglaNegocioError, modelo.DoesNotExist):
            raise
        except Exception:  # pragma: no cover
            logger.exception("editar_param")
            raise DominioError(MSG_PARAM_EDITAR_ERROR, codigo="PARAM_EDITAR_ERROR") from None

    def eliminar_param(self, ctx: AuthContext, tipo: str, id_row: int) -> str:
        modelo: Any = {"categorias": Categorias_producto, "marcas": Marcas, "tipos": Tipos_producto}[tipo]
        etiqueta = {"categorias": "Categoría", "marcas": "Marca", "tipos": "Tipo"}[tipo]
        try:
            with transaction.atomic():
                row = modelo.objects.select_for_update().get(pk=id_row)
                if tipo == "tipos" and getattr(row, "es_base", False):
                    raise ReglaNegocioError(MSG_TIPO_BASE, codigo="TIPO_BASE")
                antes = {"nombre": row.nombre, "estado": row.estado}
                row.delete()
                _audit(ctx, "ELIMINAR_PARAMETRO", modelo.__name__, id_row, antes, None)
            return MSG_PARAM_ELIMINADO.format(tipo=etiqueta)
        except (ReglaNegocioError, modelo.DoesNotExist):
            raise
        except Exception:  # pragma: no cover
            logger.exception("eliminar_param")
            raise DominioError(MSG_PARAM_ELIMINAR_ERROR, codigo="PARAM_ELIMINAR_ERROR") from None

    def plantilla_xlsx(self) -> bytes:
        from openpyxl import Workbook  # type: ignore[import-untyped]

        wb = Workbook()
        ws = wb.active
        ws.title = "productos"
        ws.append(COLUMNAS_IMPORT)
        buff = io.BytesIO()
        wb.save(buff)
        return buff.getvalue()

    def _filas_archivo(self, nombre: str, contenido: bytes) -> list[dict[str, str]]:
        lower = nombre.lower()
        if lower.endswith(".csv"):
            texto = contenido.decode("utf-8-sig")
            return [dict(r) for r in csv.DictReader(io.StringIO(texto))]
        if lower.endswith(".xlsx"):
            from openpyxl import load_workbook

            wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            headers = [str(c or "").strip() for c in rows[0]]
            out = []
            for raw in rows[1:]:
                if raw is None or all(c is None or str(c).strip() == "" for c in raw):
                    continue
                out.append({headers[i]: "" if raw[i] is None else str(raw[i]).strip() for i in range(min(len(headers), len(raw)))})
            return out
        raise ReglaNegocioError(MSG_IMPORT_FORMATO, codigo="FORMATO_ARCHIVO")

    def importar(self, ctx: AuthContext, nombre: str, contenido: bytes) -> dict[str, Any]:
        if len(contenido) > MAX_IMPORT:
            raise ReglaNegocioError(MSG_IMPORT_LIMITE, codigo="ARCHIVO_LIMITE")
        try:
            filas = self._filas_archivo(nombre, contenido)
        except ReglaNegocioError:
            raise
        except Exception:  # pragma: no cover
            raise DominioError(MSG_IMPORT_ERROR, codigo="IMPORT_ERROR") from None
        if len(filas) > 1000:
            raise ReglaNegocioError(MSG_IMPORT_LIMITE, codigo="ARCHIVO_LIMITE")
        if filas and any(c not in filas[0] for c in ("codigo_producto", "nombre", "categoria")):
            raise ReglaNegocioError(MSG_IMPORT_FORMATO, codigo="FORMATO_ARCHIVO")
        cats = {c.nombre.lower(): c for c in Categorias_producto.objects.filter(estado=True)}
        marcas = {m.nombre.lower(): m for m in Marcas.objects.filter(estado=True)}
        tipos = {t.nombre.lower(): t for t in Tipos_producto.objects.filter(estado=True)}
        ok = 0
        errores = []
        for i, fila in enumerate(filas, start=2):
            try:
                datos = {
                    "codigo_producto": fila.get("codigo_producto", ""),
                    "codigo_barras": fila.get("codigo_barras", ""),
                    "nombre": fila.get("nombre", ""),
                    "descripcion": fila.get("descripcion", ""),
                    "id_categoria": cats[fila.get("categoria", "").strip().lower()].id_categoria,
                    "id_marca": marcas[fila.get("marca", "").strip().lower()].id_marca,
                    "id_tipo_producto": tipos[fila.get("tipo_producto", "").strip().lower()].id_tipo_producto,
                    "unidad_medida": fila.get("unidad_medida", ""),
                    "precio_compra": fila.get("precio_compra", ""),
                    "precio_venta": fila.get("precio_venta", ""),
                    "iva_porcentaje": fila.get("iva_porcentaje", ""),
                    "stock_minimo": fila.get("stock_minimo", ""),
                    "inventario_habilitado": str(fila.get("inventario_habilitado", "")).strip().upper() in {"SI", "1", "TRUE", "YES"},
                    "origen": (fila.get("origen") or Productos.ORIGEN_COMPRADO).strip().lower(),
                }
                self.crear(ctx, datos)
                ok += 1
            except KeyError:
                errores.append({"fila": i, "columna": "categoria", "motivo": "Parámetro inexistente o inactivo"})
            except ReglaNegocioError as exc:
                motivo = MSG_IMPORT_EXISTE if exc.codigo in {"CODIGO_DUPLICADO", "BARRAS_DUPLICADO"} else exc.mensaje
                errores.append({"fila": i, "columna": "codigo_producto", "motivo": motivo})
            except Exception:  # pragma: no cover
                errores.append({"fila": i, "columna": "", "motivo": MSG_IMPORT_ERROR})
        return {"mensaje": MSG_IMPORT_OK.format(n=ok, m=len(errores)), "cargados": ok, "errores": errores}

    def exportar(
        self,
        q: str,
        filtros: dict[str, str],
        formato: str,
        *,
        page: int = 1,
        page_size: int = 5000,
        alcance: str = "filtro",
    ) -> tuple[str, bytes, str]:
        alcance_norm = (alcance or "filtro").strip().lower()
        if alcance_norm == "pagina":
            limite = min(max(1, page_size), 5000)
            data = self.listar(q, filtros, max(1, page), limite, "nombre")
        else:
            data = self.listar(q, filtros, 1, 5000, "nombre")
        if data["total"] == 0:
            raise ReglaNegocioError(MSG_EXPORT_VACIO, codigo="EXPORT_VACIO")
        fecha = timezone.localdate().isoformat()
        headers = [
            "codigo_producto",
            "nombre",
            "precio_compra",
            "precio_venta",
            "iva_porcentaje",
            "categoria",
            "marca",
            "tipo",
            "unidad_medida",
            "origen",
            "existencia",
            "estado",
        ]
        rows = []
        for item in data["items"]:
            origen = item.get("origen", Productos.ORIGEN_COMPRADO)
            rows.append([
                item["codigo_producto"],
                item["nombre"],
                item["precio_compra"],
                item["precio_venta"],
                item["iva_porcentaje"],
                item["categoria"],
                item["marca"],
                item["tipo"],
                item["unidad_medida"],
                ORIGEN_ETIQUETA.get(origen, origen),
                "N/A" if item["existencia"] is None else item["existencia"],
                "Activo" if item["estado"] else "Inactivo",
            ])
        if formato == "csv":
            buff = io.StringIO()
            writer = csv.writer(buff)
            writer.writerow(headers)
            writer.writerows(rows)
            return f"{fecha}-catalogo-productos.csv", buff.getvalue().encode("utf-8-sig"), "text/csv"
        if formato == "xlsx":
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.append(headers)
            for row in rows:
                ws.append(row)
            raw = io.BytesIO()
            wb.save(raw)
            return f"{fecha}-catalogo-productos.xlsx", raw.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        raise DominioError(MSG_EXPORT_ERROR, codigo="EXPORT_ERROR")
