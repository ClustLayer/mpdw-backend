"""Resumen del panel (Sprint 2) — KPIs condicionados por permiso."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Sum

from apps.m01_identidad.services import PermissionService
from apps.m03_catalogo.models import Productos
from apps.m04_inventario.models import Inventarios
from apps.m10_auditoria.bitacora_service import BitacoraAuditoriaService
from contratos.dtos import AuthContext


def _inventario_resumen() -> dict[str, Any]:
    qs = Productos.objects.filter(estado=True, inventario_habilitado=True)
    ids = list(qs.values_list("id_producto", flat=True)[:5000])
    existencias = {
        row["id_producto"]: row["total"] or Decimal("0")
        for row in Inventarios.objects.filter(id_producto_id__in=ids, id_sede__estado=True)
        .values("id_producto")
        .annotate(total=Sum("cantidad_actual"))
    }
    bajo = 0
    alertas: list[str] = []
    for p in qs.order_by("nombre"):
        total = existencias.get(p.id_producto, Decimal("0"))
        if total == 0 or total <= p.stock_minimo:
            bajo += 1
            if len(alertas) < 10:
                nivel = "agotado" if total == 0 else "bajo mínimo"
                alertas.append(f"{p.codigo_producto} — {p.nombre}: stock {nivel}")
    return {"bajo_stock_minimo": bajo, "alertas": alertas}


def _actividad_reciente() -> list[str]:
    pagina = BitacoraAuditoriaService().listar({"page": "1", "page_size": "5"})
    filas: list[str] = []
    for item in pagina.items[:5]:
        usuario = (item.get("usuario") or {}).get("nombre") or "Sistema"
        accion = item.get("accion") or ""
        entidad = item.get("entidad") or ""
        resumen = item.get("resumen") or ""
        filas.append(f"{usuario}: {accion} en {entidad} — {resumen}")
    return filas


def construir_panel_resumen(ctx: AuthContext) -> dict[str, Any]:
    perm = PermissionService()
    body: dict[str, Any] = {}
    if perm.tiene_permiso(ctx, "inventario_kardex", "Consultar"):
        body["inventario"] = _inventario_resumen()
    if perm.tiene_permiso(ctx, "auditoria", "Consultar"):
        body["actividad_reciente"] = _actividad_reciente()
    return body
