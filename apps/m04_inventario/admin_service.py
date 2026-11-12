"""Backoffice de inventario y kardex (HU 31-36, fidelidad demo)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Q, Sum

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
MSG_ENTRADAS_OK = "{n} entrada(s) registrada(s) en el kardex."
MSG_STOCK = "No hay existencias suficientes en la sede de origen."
MSG_DATOS = "Todos los campos obligatorios deben ser diligenciados."
MSG_SEDE = "La sede de destino debe ser distinta a la de origen."
MSG_PROVEEDOR = "Los productos comprados requieren proveedor."
MSG_COSTO = "El costo unitario no puede ser negativo."
MSG_LINEAS = "Agregue al menos un producto."
MSG_CODIGO = "Código no encontrado. Use SKU o código de barras registrado."


class AdminInventarioService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()

    def sedes(self) -> list[dict[str, Any]]:
        return [dict(row) for row in Sedes.objects.filter(estado=True).order_by("nombre").values("id_sede", "nombre")]

    def productos_opciones(self, q: str) -> dict[str, Any]:
        qs = Productos.objects.filter(estado=True)
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(
                Q(nombre__icontains=texto)
                | Q(codigo_producto__icontains=texto)
                | Q(codigo_barras__icontains=texto)
            )
        items = [
            {
                "id_producto": p.id_producto,
                "nombre": p.nombre,
                "codigo": p.codigo_producto,
                "codigo_barras": p.codigo_barras or "",
                "origen": p.origen,
            }
            for p in qs.order_by("nombre")[:500]
        ]
        return {"items": items, "mensaje": f"Mostrando {len(items)} productos."}

    def existencias(self, q: str, id_sede: int | None) -> dict[str, Any]:
        sedes = self.sedes()
        if id_sede:
            sedes = [s for s in sedes if s["id_sede"] == id_sede]
        productos = Productos.objects.filter(estado=True)
        if q:
            productos = productos.filter(
                Q(nombre__icontains=q) | Q(codigo_producto__icontains=q) | Q(codigo_barras__icontains=q)
            )
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
                    "origen": p.origen,
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
                    "costo_unitario": str(m.costo_unitario) if m.costo_unitario is not None else None,
                    "motivo": m.motivo,
                    "referencia": m.referencia,
                    "proveedor": m.proveedor_nombre,
                    "usuario": m.id_usuario.email if m.id_usuario_id and m.id_usuario else "",
                }
            )
        return {"items": items, "mensaje": f"Mostrando {len(items)} movimientos."}

    def entrada(self, ctx: AuthContext, datos: dict[str, Any]) -> str:
        self._validar_entrada(datos)
        return self._aplicar(ctx, "entrada_compra", datos, Decimal("1"))

    def entrada_lote(self, ctx: AuthContext, datos: dict[str, Any]) -> str:
        try:
            id_sede = int(datos.get("id_sede") or 0)
        except (TypeError, ValueError) as exc:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS") from exc
        if not id_sede:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS")
        lineas_raw = datos.get("lineas") or []
        if not isinstance(lineas_raw, list) or not lineas_raw:
            raise ReglaNegocioError(MSG_LINEAS, codigo="LINEAS")
        proveedor = str(datos.get("proveedor") or "").strip()
        referencia = str(datos.get("referencia") or "")[:80]
        motivo = str(datos.get("motivo") or "").strip() or "Entrada de mercancía"
        consolidado: dict[int, dict[str, Any]] = {}
        for linea in lineas_raw:
            if not isinstance(linea, dict):
                continue
            prod = self._resolver_producto(linea)
            try:
                cantidad = Decimal(str(linea.get("cantidad") or "0"))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ReglaNegocioError(MSG_DATOS, codigo="DATOS") from exc
            if cantidad <= 0:
                raise ReglaNegocioError(MSG_DATOS, codigo="DATOS")
            costo = self._costo_opcional(linea.get("costo_unitario"))
            pid = prod.id_producto
            if pid in consolidado:
                prev = consolidado[pid]
                consolidado[pid] = {
                    "id_producto": pid,
                    "cantidad": prev["cantidad"] + cantidad,
                    "costo_unitario": costo if costo is not None else prev.get("costo_unitario"),
                    "origen": prod.origen,
                }
            else:
                consolidado[pid] = {
                    "id_producto": pid,
                    "cantidad": cantidad,
                    "costo_unitario": costo,
                    "origen": prod.origen,
                    "nombre": prod.nombre,
                }
        if not consolidado:
            raise ReglaNegocioError(MSG_LINEAS, codigo="LINEAS")
        for row in consolidado.values():
            if row["origen"] == Productos.ORIGEN_COMPRADO and not proveedor:
                nombre = row.get("nombre", "producto")
                raise ReglaNegocioError(f"«{nombre}» es comprado: el proveedor es obligatorio.", codigo="PROVEEDOR")
        with transaction.atomic():
            n = 0
            for row in consolidado.values():
                payload = {
                    "id_producto": row["id_producto"],
                    "id_sede": id_sede,
                    "cantidad": row["cantidad"],
                    "motivo": motivo,
                    "referencia": referencia,
                    "proveedor": proveedor,
                    "costo_unitario": row.get("costo_unitario"),
                }
                self._aplicar(ctx, "entrada_compra", payload, Decimal("1"), requiere_motivo=False)
                n += 1
        return MSG_ENTRADAS_OK.format(n=n)

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

    def _resolver_producto(self, linea: dict[str, Any]) -> Productos:
        if linea.get("id_producto"):
            try:
                return Productos.objects.get(pk=int(linea["id_producto"]), estado=True)
            except (Productos.DoesNotExist, TypeError, ValueError) as exc:
                raise ReglaNegocioError(MSG_CODIGO, codigo="PRODUCTO") from exc
        codigo = str(linea.get("codigo") or "").strip()
        if not codigo:
            raise ReglaNegocioError(MSG_CODIGO, codigo="PRODUCTO")
        prod = Productos.objects.filter(estado=True).filter(
            Q(codigo_producto__iexact=codigo) | Q(codigo_barras__iexact=codigo)
        ).first()
        if not prod:
            raise ReglaNegocioError(MSG_CODIGO, codigo="PRODUCTO")
        return prod

    def _costo_opcional(self, valor: Any) -> Decimal | None:
        if valor in (None, ""):
            return None
        try:
            costo = Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ReglaNegocioError(MSG_COSTO, codigo="COSTO") from exc
        if costo < 0:
            raise ReglaNegocioError(MSG_COSTO, codigo="COSTO")
        return costo

    def _validar_entrada(self, datos: dict[str, Any]) -> None:
        try:
            id_producto = int(datos.get("id_producto") or 0)
        except (TypeError, ValueError) as exc:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS") from exc
        if not id_producto:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS")
        producto = Productos.objects.filter(pk=id_producto, estado=True).first()
        if not producto:
            raise ReglaNegocioError(MSG_CODIGO, codigo="PRODUCTO")
        proveedor = str(datos.get("proveedor") or "").strip()
        if producto.origen == Productos.ORIGEN_COMPRADO and not proveedor:
            raise ReglaNegocioError(MSG_PROVEEDOR, codigo="PROVEEDOR")
        costo = self._costo_opcional(datos.get("costo_unitario"))
        if costo is not None:
            datos["costo_unitario"] = costo

    def _aplicar(
        self,
        ctx: AuthContext,
        tipo: str,
        datos: dict[str, Any],
        signo: Decimal,
        *,
        requiere_motivo: bool | None = None,
    ) -> str:
        try:
            id_producto = int(datos.get("id_producto") or 0)
            id_sede = int(datos.get("id_sede") or 0)
            cantidad = Decimal(str(datos.get("cantidad") or "0"))
        except Exception as exc:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS") from exc
        motivo = str(datos.get("motivo") or "").strip()
        if requiere_motivo is None:
            requiere_motivo = tipo != "entrada_compra"
        if not id_producto or not id_sede or cantidad <= 0:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS")
        if requiere_motivo and not motivo:
            raise ReglaNegocioError(MSG_DATOS, codigo="DATOS")
        if not motivo and tipo == "entrada_compra":
            motivo = "Entrada de mercancía"
        costo = datos.get("costo_unitario")
        if costo not in (None, ""):
            costo = self._costo_opcional(costo)
        else:
            costo = None
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
                costo_unitario=costo,
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
