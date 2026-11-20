"""Catálogo público (HU 88–89)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from apps.m03_catalogo.models import Categorias_producto, Marcas, Productos, Tipos_producto
from apps.m04_inventario.models import Inventarios
from apps.m12_tienda_publica import mensajes as msg
from apps.m12_tienda_publica.slug_util import parse_id_producto, ruta_producto, slugify_nombre
from contratos.excepciones import ReglaNegocioError

ORDENES = {
    "destacados": ("-id_producto",),
    "precio_asc": ("precio_venta", "nombre"),
    "precio_desc": ("-precio_venta", "nombre"),
    "nombre_asc": ("nombre",),
    "nombre_desc": ("-nombre",),
}


def _decimal_opcional(val: str | None) -> Decimal | None:
    if val in (None, ""):
        return None
    try:
        d = Decimal(str(val))
    except (InvalidOperation, TypeError) as exc:
        raise ReglaNegocioError(msg.MSG_CATALOGO_FALLA, codigo="VALIDACION") from exc
    if d < 0:
        raise ReglaNegocioError(msg.MSG_CATALOGO_FALLA, codigo="VALIDACION")
    return d


def _stock_disponible(id_producto: int, id_sede: int | None) -> Decimal:
    qs = Inventarios.objects.filter(id_producto_id=id_producto)
    if id_sede:
        qs = qs.filter(id_sede_id=id_sede)
    agg = qs.aggregate(total=Coalesce(Sum("cantidad_actual"), Decimal("0")))
    return Decimal(str(agg["total"] or 0))


def _disponible(prod: Productos, id_sede: int | None) -> bool:
    if not prod.estado:
        return False
    if not prod.inventario_habilitado:
        return True
    return _stock_disponible(prod.id_producto, id_sede) > 0


def _imagen_url(prod: Productos) -> str:
    url = (prod.imagen_url or "").strip()
    if not url:
        return ""
    if url.startswith("http"):
        return url
    return f"/api/v1/catalogo/media/{url.lstrip('/')}/"


def _serializar_corto(prod: Productos, id_sede: int | None) -> dict[str, Any]:
    disp = _disponible(prod, id_sede)
    marca = prod.id_marca.nombre if prod.id_marca else ""
    categoria = prod.id_categoria.nombre if prod.id_categoria else ""
    return {
        "id_producto": prod.id_producto,
        "slug": ruta_producto(prod.id_producto, prod.nombre),
        "codigo_producto": prod.codigo_producto,
        "nombre": prod.nombre,
        "marca": marca,
        "categoria": categoria,
        "precio_venta": str(prod.precio_venta),
        "unidad_medida": prod.unidad_medida,
        "agotado": not disp,
        "imagen_url": _imagen_url(prod),
        "imagen_alt": prod.nombre,
    }


def _seo(prod: Productos) -> dict[str, Any]:
    slug = ruta_producto(prod.id_producto, prod.nombre)
    desc = (prod.descripcion or prod.nombre)[:300]
    return {
        "titulo": f"{prod.nombre} | Mundo Pinturas Diana",
        "descripcion": desc,
        "canonical": f"/producto/{slug}",
        "og_type": "product",
        "og_title": prod.nombre,
        "og_description": desc,
        "schema_org_product": {
            "@type": "Product",
            "name": prod.nombre,
            "sku": prod.codigo_producto,
            "offers": {"@type": "Offer", "price": str(prod.precio_venta), "priceCurrency": "COP"},
        },
    }


class TiendaCatalogoService:
    def filtros(self) -> dict[str, Any]:
        cats = [
            {"id": c.id_categoria, "nombre": c.nombre, "slug": slugify_nombre(c.nombre)}
            for c in Categorias_producto.objects.filter(estado=True).order_by("nombre")
        ]
        marcas = [{"id": m.id_marca, "nombre": m.nombre} for m in Marcas.objects.filter(estado=True).order_by("nombre")]
        tipos = [
            {"id": t.id_tipo_producto, "nombre": t.nombre}
            for t in Tipos_producto.objects.filter(estado=True).order_by("nombre")
        ]
        return {"categorias": cats, "marcas": marcas, "tipos_producto": tipos}

    def listar(
        self,
        q: str | None,
        id_categoria: int | None,
        id_marca: int | None,
        id_tipo: int | None,
        precio_min: str | None,
        precio_max: str | None,
        orden: str | None,
        page: int,
        page_size: int,
        id_sede: int | None,
    ) -> dict[str, Any]:
        pmin = _decimal_opcional(precio_min)
        pmax = _decimal_opcional(precio_max)
        if pmin is not None and pmax is not None and pmin > pmax:
            raise ReglaNegocioError(msg.MSG_PRECIO_RANGO, codigo="VALIDACION")

        qs = Productos.objects.filter(estado=True).select_related("id_categoria", "id_marca")
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(codigo_producto__icontains=texto)
                | Q(id_marca__nombre__icontains=texto)
            )
        if id_categoria:
            qs = qs.filter(id_categoria_id=id_categoria)
        if id_marca:
            qs = qs.filter(id_marca_id=id_marca)
        if id_tipo:
            qs = qs.filter(id_tipo_producto_id=id_tipo)
        if pmin is not None:
            qs = qs.filter(precio_venta__gte=pmin)
        if pmax is not None:
            qs = qs.filter(precio_venta__lte=pmax)

        orden_norm = (orden or "destacados").strip().lower()
        qs = qs.order_by(*ORDENES.get(orden_norm, ORDENES["destacados"]))
        total = qs.count()
        start = (page - 1) * page_size
        page_qs = list(qs[start : start + page_size])
        if not total:
            return {
                "mensaje": msg.MSG_CATALOGO_VACIO,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }
        items = [_serializar_corto(p, id_sede) for p in page_qs]
        return {
            "mensaje": msg.MSG_CATALOGO_OK.format(n=len(items)),
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def detalle(self, slug_o_id: str, id_sede: int | None) -> dict[str, Any]:
        pid = parse_id_producto(slug_o_id)
        if not pid:
            raise ReglaNegocioError(msg.MSG_PRODUCTO_NO, codigo="NO_ENCONTRADO")
        prod = (
            Productos.objects.select_related("id_categoria", "id_marca", "id_tipo_producto")
            .filter(pk=pid, estado=True)
            .first()
        )
        if not prod:
            raise ReglaNegocioError(msg.MSG_PRODUCTO_NO, codigo="NO_ENCONTRADO")
        impuesto = "Incluye IVA / Impoconsumo" if prod.iva_porcentaje else "Precio con impuestos incluidos"
        item = {
            **_serializar_corto(prod, id_sede),
            "descripcion": prod.descripcion or "",
            "tipo_producto": prod.id_tipo_producto.nombre if prod.id_tipo_producto else "",
            "nota_impuestos": impuesto,
            "seo": _seo(prod),
        }
        return {"item": item}
