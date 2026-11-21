"""Resumen del panel (Sprint 2+) — KPIs condicionados por permiso."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.m01_identidad.services import PermissionService
from apps.m03_catalogo.models import Productos
from apps.m04_inventario.models import Inventarios
from apps.m06_ventas.models import Facturas, Facturas_electronicas
from apps.m07_domicilios.models import Entregas
from apps.m10_auditoria.bitacora_service import BitacoraAuditoriaService
from contratos.dtos import AuthContext

ESTADOS_DOM_ACTIVOS = ("PENDIENTE", "ASIGNADO", "EN_CAMINO")


def _inventario_resumen() -> dict[str, Any]:
    qs = Productos.objects.filter(estado=True, inventario_habilitado=True).only(
        "id_producto", "codigo_producto", "nombre", "stock_minimo"
    )
    existencias = {
        row["id_producto"]: row["total"] or Decimal("0")
        for row in Inventarios.objects.filter(id_sede__estado=True)
        .values("id_producto")
        .annotate(total=Coalesce(Sum("cantidad_actual"), Decimal("0")))
    }
    filas: list[tuple[Decimal, Productos]] = []
    bajo = 0
    for p in qs:
        total = existencias.get(p.id_producto, Decimal("0"))
        if total == 0 or total <= p.stock_minimo:
            bajo += 1
            filas.append((total, p))
    filas.sort(key=lambda x: (x[0], x[1].nombre.lower()))
    productos_bajo: list[dict[str, Any]] = []
    alertas: list[str] = []
    for total, p in filas[:5]:
        nivel = "agotado" if total == 0 else "bajo mínimo"
        etiqueta = f"{p.codigo_producto} — {p.nombre}: stock {nivel}"
        alertas.append(etiqueta)
        productos_bajo.append(
            {
                "id_producto": p.id_producto,
                "codigo": p.codigo_producto,
                "nombre": p.nombre,
                "stock_total": float(total),
                "stock_minimo": int(p.stock_minimo),
                "nivel": nivel,
            }
        )
    return {"bajo_stock_minimo": bajo, "alertas": alertas, "productos_bajo_stock": productos_bajo}


def _actividad_reciente() -> list[dict[str, Any]]:
    pagina = BitacoraAuditoriaService().listar({"page": "1", "page_size": "5"})
    return list(pagina.items[:5])


def _ventas_hoy(ctx: AuthContext, perm: PermissionService) -> dict[str, Any]:
    hoy = timezone.localdate()
    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(hoy, time.min), tz)
    fin = timezone.make_aware(datetime.combine(hoy, time.max), tz)
    qs = Facturas.objects.filter(fecha_hora__gte=inicio, fecha_hora__lte=fin).exclude(estado="ANULADA")
    if not perm.tiene_permiso(ctx, "facturas", "Total"):
        qs = qs.filter(id_usuario_id=ctx.id_usuario)
    count = qs.count()
    total = qs.aggregate(t=Coalesce(Sum("total"), Decimal("0")))["t"] or Decimal("0")
    return {"cantidad": count, "total": float(total)}


def _domicilios_pendientes() -> int:
    return Entregas.objects.filter(estado__in=ESTADOS_DOM_ACTIVOS).count()


def _fe_pendientes() -> int:
    return Facturas_electronicas.objects.filter(estado="PENDIENTE").count()


def construir_panel_resumen(ctx: AuthContext) -> dict[str, Any]:
    perm = PermissionService()
    body: dict[str, Any] = {}
    if perm.tiene_permiso(ctx, "facturas", "Consultar") or perm.tiene_permiso(ctx, "pos", "Crear"):
        body["ventas_hoy"] = _ventas_hoy(ctx, perm)
    if perm.tiene_permiso(ctx, "domicilios", "Consultar"):
        body["domicilios_pendientes"] = _domicilios_pendientes()
    if perm.tiene_permiso(ctx, "facturacion_electronica", "Consultar"):
        body["facturas_electronicas_pendientes"] = _fe_pendientes()
    if perm.tiene_permiso(ctx, "inventario_kardex", "Consultar"):
        body["inventario"] = _inventario_resumen()
    if perm.tiene_permiso(ctx, "auditoria", "Consultar"):
        body["actividad_reciente"] = _actividad_reciente()
    return body
