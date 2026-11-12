"""Backoffice de inventario y kardex (HU 31-36, fidelidad demo)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum

from apps.m01_identidad.models import Usuarios
from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Productos
from apps.m04_inventario.models import Inventarios, Movimientos_inventario
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

SIGNOS = {
    "entrada_compra": Decimal("1"),
    "ajuste_positivo": Decimal("1"),
    "ajuste_negativo": Decimal("-1"),
    "merma": Decimal("-1"),
    "traslado_salida": Decimal("-1"),
    "traslado_entrada": Decimal("1"),
}
MSG_OK = "Movimiento registrado correctamente."
MSG_STOCK = "No hay existencias suficientes en la sede de origen."
MSG_DATOS = "Todos los campos obligatorios deben ser diligenciados."
MSG_SEDE = "La sede de destino debe ser distinta a la de origen."


class AdminInventarioService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def sedes(self) -> list[dict[str, Any]]:
        return [dict(row) for row in Sedes.objects.filter(estado=True).order_by("nombre").values("id_sede", "nombre")]

    def existencias(self, q: str, id_sede: int | None) -> dict[str, Any]:
        sedes = self.sedes()
        if id_sede:
            sedes = [s for s in sedes if s["id_sede"] == id_sede]
        productos = Productos.objects.filter(estado=True).select_related("id_tipo_producto")
        if q:
            productos = productos.filter(nombre__icontains=q) | productos.filter(codigo_producto__icontains=q)
        productos = productos.order_by("nombre")[:200]
        ids = [p.id_producto for p in productos]
        invs = Inventarios.objects.filter(id_producto_id__in=ids, id_sede__estado=True)
        celdas: dict[tuple[int, int], Decimal] = {(i.id_producto_id, i.id_sede_id): i.cantidad_actual for i in invs}
        filas = []
        bajos: list[str] = []
        for p in productos:
            cells = {str(s["id_sede"]): float(celdas.get((p.id_producto, s["id_sede"]), 0)) for s in sedes}
            total = sum(cells.values())
            minimo = float(p.stock_minimo or 0)
            if minimo > 0 and any(v <= minimo for v in cells.values()):
                bajos.append(p.nombre)
            filas.append(
                {
                    "id_producto": p.id_producto,
                    "nombre": p.nombre,
                    "codigo": p.codigo_producto,
                    "origen": getattr(p.id_tipo_producto, "nombre", "") or "Comprado",
                    "unidad": p.unidad_medida,
                    "minimo": minimo,
                    "celdas": cells,
                    "total": total,
                }
            )
        return {"sedes": sedes, "items": filas, "alerta": bajos, "mensaje": f"Mostrando {len(filas)} productos."}

    def kardex(self, filtros: dict[str, str]) -> dict[str, Any]:
        qs = Movimientos_inventario.objects.select_related(
            "id_inventario__id_producto", "id_inventario__id_sede", "id_usuario"
        )
        if filtros.get("id_sede"):
            qs = qs.filter(id_inventario__id_sede_id=int(filtros["id_sede"]))
        if filtros.get("tipo"):
            qs = qs.filter(tipo_movimiento=filtros["tipo"])
        if filtros.get("desde"):
            qs = qs.filter(fecha_hora__date__gte=filtros["desde"])
        if filtros.get("hasta"):
            qs = qs.filter(fecha_hora__date__lte=filtros["hasta"])
        items = []
        for m in qs.order_by("-fecha_hora")[:200]:
            signo = SIGNOS.get(m.tipo_movimiento, Decimal("1"))
            delta = float(m.cantidad * signo) if m.tipo_movimiento in SIGNOS else float(m.cantidad_nueva - m.cantidad_anterior)
            items.append(
                {
                    "id_movimiento": m.id_movimiento,
                    "fecha": m.fecha_hora.isoformat(),
                    "producto": m.id_inventario.id_producto.nombre,
                    "sede": m.id_inventario.id_sede.nombre,
                    "tipo": m.tipo_movimiento,
                    "cantidad": float(m.cantidad),
                    "delta": delta,
                    "anterior": float(m.cantidad_anterior),
                    "nueva": float(m.cantidad_nueva),
                    "motivo": m.motivo,
                    "referencia": m.referencia,
                    "proveedor": m.proveedor_nombre,
                    "usuario": m.id_usuario.email if m.id_usuario_id and m.id_usuario else "",
                }
            )
        return {"items": items, "mensaje": f"Mostrando {len(items)} movimientos."}

    def entrada(self, ctx: AuthContext, datos: dict[str, Any]) -> str:
        return self._aplicar(ctx, "entrada_compra", datos, Decimal("1"))

    def ajuste(self, ctx: AuthContext, datos: dict[str, Any]) -> str:
        tipo = str(datos.get("tipo") or "ajuste_positivo")
        if tipo not in {"ajuste_positivo", "ajuste_negativo", "merma"}:
            raise ReglaNegocioError(MSG_DATOS, codigo="TIPO")
        return self._aplicar(ctx, tipo, datos, SIGNOS[tipo])

    def traslado(self, ctx: AuthContext, datos: dict[str, Any]) -> str:
        origen = int(datos.get("id_sede") or 0)
        destino = int(datos.get("id_sede_destino") or 0)
        if not origen or not destino or origen == destino:
            raise ReglaNegocioError(MSG_SEDE, codigo="SEDE")
        with transaction.atomic():
            self._aplicar(ctx, "traslado_salida", datos, Decimal("-1"))
            self._aplicar(ctx, "traslado_entrada", {**datos, "id_sede": destino}, Decimal("1"))
        return MSG_OK

    def _aplicar(self, ctx: AuthContext, tipo: str, datos: dict[str, Any], signo: Decimal) -> str:
        try:
            id_producto = int(datos.get("id_producto") or 0)
            id_sede = int(datos.get("id_sede") or 0)
            cantidad = Decimal(str(datos.get("cantidad") or "0"))
        except Exception as exc:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS") from exc
        motivo = str(datos.get("motivo") or "").strip()
        if not id_producto or not id_sede or cantidad <= 0 or not motivo:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS")
        with transaction.atomic():
            inv, _ = Inventarios.objects.select_for_update().get_or_create(
                id_producto_id=id_producto,
                id_sede_id=id_sede,
                defaults={"cantidad_actual": 0, "cantidad_reservada": 0},
            )
            anterior = inv.cantidad_actual
            nueva = anterior + (cantidad * signo)
            if nueva < 0:
                raise ReglaNegocioError(MSG_STOCK, codigo="STOCK")
            inv.cantidad_actual = nueva
            inv.save(update_fields=["cantidad_actual"])
            usuario_id = ctx.id_usuario if Usuarios.objects.filter(pk=ctx.id_usuario).exists() else None
            Movimientos_inventario.objects.create(
                id_inventario=inv,
                tipo_movimiento=tipo,
                cantidad=cantidad,
                cantidad_anterior=anterior,
                cantidad_nueva=nueva,
                motivo=motivo,
                referencia=str(datos.get("referencia") or "")[:80],
                proveedor_nombre=str(datos.get("proveedor") or "")[:255],
                id_usuario_id=usuario_id,
            )
        self._audit.registrar(
            AuditoriaDTO(
                id_usuario=usuario_id,
                accion="INVENTARIO",
                entidad="Movimientos_inventario",
                id_entidad=id_producto,
                datos_antes={"cantidad": str(anterior)},
                datos_despues={"cantidad": str(nueva), "tipo": tipo},
                motivo=motivo,
                id_correlacion=ctx.id_correlacion,
                ip=ctx.ip,
                user_agent=ctx.user_agent,
            )
        )
        return MSG_OK

    def totales(self) -> dict[str, Any]:
        total = Inventarios.objects.filter(id_sede__estado=True).aggregate(s=Sum("cantidad_actual"))["s"] or 0
        return {"existencia_total": float(total)}
