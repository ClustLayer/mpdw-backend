"""CRUD de escaparates del inicio y consulta pública."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.m03_catalogo.models import Productos
from apps.m12_tienda_publica.models import Escaparate_producto, Escaparate_seccion
from apps.m12_tienda_publica.tienda_catalogo_service import _serializar_corto
from contratos.excepciones import ReglaNegocioError


def _serializar_seccion(row: Escaparate_seccion, *, productos: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id_escaparate": row.id_escaparate,
        "clave": row.clave,
        "frase": row.frase,
        "titulo": row.titulo,
        "enlace_catalogo": row.enlace_catalogo,
        "color_acento": row.color_acento,
        "orden": row.orden,
        "estado": row.estado,
        "version_fila": row.version_fila,
        "productos": productos or [],
    }


class EscaparateService:
    def listar_publico(self, id_sede: int | None = None) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for sec in Escaparate_seccion.objects.filter(estado=True).order_by("orden", "titulo"):
            ids = list(
                Escaparate_producto.objects.filter(id_escaparate=sec)
                .order_by("orden", "id_producto_id")
                .values_list("id_producto_id", flat=True)
            )
            prods = []
            for pid in ids:
                p = Productos.objects.filter(pk=pid, estado=True).select_related("id_categoria", "id_marca").first()
                if p:
                    prods.append(_serializar_corto(p, id_sede))
            if prods:
                items.append(_serializar_seccion(sec, productos=prods))
        return {"items": items}

    def listar_admin(self) -> dict[str, Any]:
        items = [
            _serializar_seccion(
                sec,
                productos=[
                    {"id_producto": ep.id_producto_id, "nombre": ep.id_producto.nombre, "orden": ep.orden}
                    for ep in Escaparate_producto.objects.filter(id_escaparate=sec)
                    .select_related("id_producto")
                    .order_by("orden", "id_producto_id")
                ],
            )
            for sec in Escaparate_seccion.objects.all().order_by("orden", "titulo")
        ]
        return {"items": items, "mensaje": f"{len(items)} sección(es) configuradas."}

    @transaction.atomic
    def crear(self, datos: dict[str, Any]) -> dict[str, Any]:
        clave = (datos.get("clave") or "").strip().lower().replace(" ", "-")
        if not clave or not datos.get("titulo"):
            raise ReglaNegocioError("La clave y el título son obligatorios.", codigo="VALIDACION")
        if Escaparate_seccion.objects.filter(clave=clave).exists():
            raise ReglaNegocioError("Ya existe una sección con esa clave.", codigo="DUPLICADO")
        row = Escaparate_seccion.objects.create(
            clave=clave,
            frase=(datos.get("frase") or "").strip()[:160],
            titulo=(datos.get("titulo") or "").strip()[:160],
            enlace_catalogo=(datos.get("enlace_catalogo") or "/catalogo").strip()[:255],
            color_acento=(datos.get("color_acento") or "#E11D74").strip()[:16],
            orden=int(datos.get("orden") or 0),
            estado=bool(datos.get("estado", True)),
        )
        return {"escaparate": _serializar_seccion(row), "mensaje": "Sección creada."}

    @transaction.atomic
    def actualizar(self, pk: int, datos: dict[str, Any]) -> dict[str, Any]:
        row = Escaparate_seccion.objects.filter(pk=pk).first()
        if not row:
            raise ReglaNegocioError("Sección no encontrada.", codigo="NO_ENCONTRADO")
        if int(datos.get("version_fila", row.version_fila)) != row.version_fila:
            raise ReglaNegocioError("Otro usuario modificó la sección.", codigo="CONFLICTO")
        row.frase = (datos.get("frase") or row.frase).strip()[:160]
        row.titulo = (datos.get("titulo") or row.titulo).strip()[:160]
        row.enlace_catalogo = (datos.get("enlace_catalogo") or row.enlace_catalogo).strip()[:255]
        row.color_acento = (datos.get("color_acento") or row.color_acento).strip()[:16]
        row.orden = int(datos.get("orden", row.orden))
        if "estado" in datos:
            row.estado = bool(datos["estado"])
        row.version_fila += 1
        row.save()
        return {"escaparate": _serializar_seccion(row), "mensaje": "Sección actualizada."}

    @transaction.atomic
    def asignar_productos(self, pk: int, ids: list[int]) -> dict[str, Any]:
        row = Escaparate_seccion.objects.filter(pk=pk).first()
        if not row:
            raise ReglaNegocioError("Sección no encontrada.", codigo="NO_ENCONTRADO")
        Escaparate_producto.objects.filter(id_escaparate=row).delete()
        for orden, pid in enumerate(ids):
            if Productos.objects.filter(pk=pid, estado=True).exists():
                Escaparate_producto.objects.create(id_escaparate=row, id_producto_id=pid, orden=orden)
        return {"mensaje": "Productos asignados.", "escaparate": _serializar_seccion(row)}
