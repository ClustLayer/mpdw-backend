"""Épica 11 — caja, jornada, movimientos y cuadre (HU 60–79)."""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, TypeVar

from django.db import transaction
from django.db.models import Model, Q, Sum
from django.utils import timezone

from apps.m02_sedes.models import Sedes
from apps.m05_clientes.mensajes import MSG_CONCURRENCIA
from apps.m06_ventas.repositories import SalesReadAdapter
from apps.m08_caja import mensajes as msg
from apps.m08_caja.admin_caja_service import AdminCajaService, _enmascarar_numero
from apps.m08_caja.dominio import VarianteCalculoEfectivo, calcular_efectivo_esperado
from apps.m08_caja.models import (
    TIPOS_CATEGORIA_MOV,
    Adiciones_base,
    Ahorros,
    Categorias_movimiento,
    Conceptos_movimiento,
    Entregas_dinero,
    Gastos_caja,
    Reportes_diarios,
    Transferencias_caja,
)
from apps.m10_auditoria.services import AuditService
from contratos.dtos import AuditoriaDTO, AuthContext
from contratos.excepciones import ReglaNegocioError

TIPOS_VALIDOS_CAT = frozenset(TIPOS_CATEGORIA_MOV)
_TIPO_ALIAS = {
    "gasto": "Gasto",
    "transferencia": "Transferencia",
    "ahorro": "Ahorro",
    "Gasto": "Gasto",
    "Transferencia": "Transferencia",
    "Ahorro": "Ahorro",
}


def _norm_tipo_categoria(tipo: str) -> str:
    bruto = (tipo or "").strip()
    return _TIPO_ALIAS.get(bruto) or _TIPO_ALIAS.get(bruto.lower()) or ""


_Model = TypeVar("_Model", bound=Model)


def enmascarar_numero(numero: str) -> str:
    return _enmascarar_numero(numero)


def _dec(val: Any, *, positivo: bool = True) -> Decimal:
    try:
        d = Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION") from exc
    if positivo and d <= 0:
        raise ReglaNegocioError(msg.MSG_VALOR_POSITIVO, codigo="VALIDACION")
    return d


def _assert_sede(ctx: AuthContext, id_sede: int) -> Sedes:
    sede = Sedes.objects.filter(pk=id_sede, estado=True).first()
    if not sede:
        raise ReglaNegocioError(msg.MSG_SEDE, codigo="VALIDACION")
    if not ctx.es_global and id_sede not in ctx.sedes_asignadas:
        raise ReglaNegocioError(msg.MSG_SEDE, codigo="NO_AUTORIZADO")
    return sede


def _auditar(
    ctx: AuthContext, accion: str, entidad: str, entidad_id: int, motivo: str, audit: AuditService
) -> None:
    audit.registrar(
        AuditoriaDTO(
            id_usuario=ctx.id_usuario,
            accion=accion,
            entidad=entidad,
            id_entidad=entidad_id,
            motivo=motivo,
            id_correlacion=ctx.id_correlacion,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    )


def _serializar_reporte(r: Reportes_diarios) -> dict[str, Any]:
    return {
        "id_reporte_diario": r.id_reporte_diario,
        "id_sede": r.id_sede_id,
        "fecha": r.fecha.isoformat(),
        "estado": r.estado,
        "base_inicial": str(r.base_inicial),
        "base_adicional": str(r.base_adicional or 0),
        "venta_registrada": str(r.venta_registrada) if r.venta_registrada is not None else None,
        "total_ventas": str(r.total_ventas),
        "total_gastos": str(r.total_gastos),
        "total_ahorros": str(r.total_ahorros),
        "total_transferencias": str(r.total_transferencias),
        "total_entregas": str(r.total_entregas),
        "efectivo_esperado": str(r.efectivo_esperado) if r.efectivo_esperado is not None else None,
        "efectivo_declarado": str(r.efectivo_declarado)
        if r.efectivo_declarado is not None
        else None,
        "diferencia": str(r.diferencia) if r.diferencia is not None else None,
        "observaciones": r.observaciones,
        "version_fila": r.version_fila,
    }


class CajaEpic11Service:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or AuditService()
        self._ventas = SalesReadAdapter()

    # —— Catálogos ——
    def listar_categorias(self, tipo: str | None, q: str) -> dict[str, Any]:
        qs = Categorias_movimiento.objects.all().order_by("nombre")
        if tipo:
            tip = _norm_tipo_categoria(tipo)
            if tip:
                qs = qs.filter(tipo_movimiento=tip)
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(Q(nombre__icontains=texto) | Q(descripcion__icontains=texto))
        items = [
            {
                "id_categoria_movimiento": c.id_categoria_movimiento,
                "nombre": c.nombre,
                "tipo_movimiento": c.tipo_movimiento,
                "descripcion": c.descripcion,
                "estado": c.estado,
                "version_fila": c.version_fila,
            }
            for c in qs
        ]
        return {
            "items": items,
            "total": len(items),
            "mensaje": msg.MSG_CAT_LISTADO.format(n=len(items)),
        }

    @transaction.atomic
    def crear_categoria(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        nombre = (datos.get("nombre") or "").strip()
        tipo = _norm_tipo_categoria(str(datos.get("tipo_movimiento") or ""))
        if not nombre or tipo not in TIPOS_VALIDOS_CAT:
            raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION")
        c = Categorias_movimiento.objects.create(
            nombre=nombre[:100],
            tipo_movimiento=tipo,
            descripcion=str(datos.get("descripcion") or "")[:2000],
            estado=bool(datos.get("estado", True)),
        )
        _auditar(
            ctx,
            "CREAR_CATEGORIA_CAJA",
            "Categorias_movimiento",
            c.id_categoria_movimiento,
            nombre,
            self._audit,
        )
        item = {
            "id_categoria_movimiento": c.id_categoria_movimiento,
            "nombre": c.nombre,
            "tipo_movimiento": c.tipo_movimiento,
            "descripcion": c.descripcion,
            "estado": c.estado,
            "version_fila": c.version_fila,
        }
        return {"mensaje": msg.MSG_CAT_CREADA, "item": item}

    @transaction.atomic
    def actualizar_categoria(
        self, ctx: AuthContext, pk: int, datos: dict[str, Any]
    ) -> dict[str, Any]:
        c = Categorias_movimiento.objects.select_for_update().filter(pk=pk).first()
        if not c:
            raise ReglaNegocioError(msg.MSG_NO_ENCONTRADO, codigo="NO_ENCONTRADO")
        if int(datos.get("version_fila") or 0) != c.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        nombre = (datos.get("nombre") or c.nombre).strip()
        tipo = _norm_tipo_categoria(str(datos.get("tipo_movimiento") or c.tipo_movimiento))
        if not nombre or tipo not in TIPOS_VALIDOS_CAT:
            raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION")
        c.nombre = nombre[:100]
        c.tipo_movimiento = tipo
        c.descripcion = str(datos.get("descripcion") or c.descripcion)[:2000]
        if "estado" in datos:
            c.estado = bool(datos.get("estado"))
        c.version_fila += 1
        c.save()
        _auditar(
            ctx,
            "EDITAR_CATEGORIA_CAJA",
            "Categorias_movimiento",
            c.id_categoria_movimiento,
            nombre,
            self._audit,
        )
        item = next(
            x
            for x in self.listar_categorias(None, nombre)["items"]
            if x["id_categoria_movimiento"] == pk
        )
        return {"mensaje": msg.MSG_CAT_ACTUALIZADA, "item": item}

    def listar_conceptos(self, tipo: str | None, q: str) -> dict[str, Any]:
        qs = Conceptos_movimiento.objects.select_related("id_categoria").order_by("nombre")
        if tipo:
            qs = qs.filter(id_categoria__tipo_movimiento=tipo)
        texto = (q or "").strip()
        if texto:
            qs = qs.filter(Q(nombre__icontains=texto) | Q(descripcion__icontains=texto))
        items = [
            {
                "id_concepto_movimiento": c.id_concepto_movimiento,
                "nombre": c.nombre,
                "id_categoria": c.id_categoria_id,
                "id_categoria_movimiento": c.id_categoria_id,
                "categoria_nombre": c.id_categoria.nombre,
                "tipo_movimiento": c.id_categoria.tipo_movimiento,
                "valor_sugerido": str(c.valor_sugerido) if c.valor_sugerido is not None else None,
                "descripcion": c.descripcion,
                "detalle_sugerido": c.descripcion,
                "estado": c.estado,
                "version_fila": c.version_fila,
            }
            for c in qs
        ]
        return {"items": items, "mensaje": msg.MSG_CON_LISTADO.format(n=len(items))}

    @transaction.atomic
    def crear_concepto(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        nombre = (datos.get("nombre") or "").strip()
        id_cat = int(datos.get("id_categoria") or datos.get("id_categoria_movimiento") or 0)
        cat = Categorias_movimiento.objects.filter(pk=id_cat, estado=True).first()
        if not nombre or not cat:
            raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION")
        sugerido = datos.get("valor_sugerido")
        vs = _dec(sugerido, positivo=False) if sugerido not in (None, "") else None
        detalle = str(datos.get("descripcion") or datos.get("detalle_sugerido") or "")[:2000]
        c = Conceptos_movimiento.objects.create(
            nombre=nombre[:255],
            id_categoria=cat,
            valor_sugerido=vs,
            descripcion=detalle,
            estado=bool(datos.get("estado", True)),
        )
        _auditar(
            ctx,
            "CREAR_CONCEPTO_CAJA",
            "Conceptos_movimiento",
            c.id_concepto_movimiento,
            nombre,
            self._audit,
        )
        item = {
            "id_concepto_movimiento": c.id_concepto_movimiento,
            "nombre": c.nombre,
            "id_categoria": c.id_categoria_id,
            "tipo_movimiento": cat.tipo_movimiento,
            "valor_sugerido": str(c.valor_sugerido) if c.valor_sugerido is not None else None,
            "descripcion": c.descripcion,
            "estado": c.estado,
            "version_fila": c.version_fila,
        }
        return {"mensaje": msg.MSG_CON_CREADO, "item": item}

    @transaction.atomic
    def actualizar_concepto(
        self, ctx: AuthContext, pk: int, datos: dict[str, Any]
    ) -> dict[str, Any]:
        c = (
            Conceptos_movimiento.objects.select_for_update()
            .select_related("id_categoria")
            .filter(pk=pk)
            .first()
        )
        if not c:
            raise ReglaNegocioError(msg.MSG_NO_ENCONTRADO, codigo="NO_ENCONTRADO")
        if int(datos.get("version_fila") or 0) != c.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        nombre = (datos.get("nombre") or c.nombre).strip()
        if not nombre:
            raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION")
        id_cat_in = datos.get("id_categoria") or datos.get("id_categoria_movimiento")
        if id_cat_in:
            cat = Categorias_movimiento.objects.filter(pk=int(id_cat_in), estado=True).first()
            if not cat:
                raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION")
            c.id_categoria = cat
        if "valor_sugerido" in datos:
            raw = datos.get("valor_sugerido")
            c.valor_sugerido = _dec(raw, positivo=False) if raw not in (None, "") else None
        c.nombre = nombre[:255]
        if "descripcion" in datos or "detalle_sugerido" in datos:
            c.descripcion = str(datos.get("descripcion") or datos.get("detalle_sugerido") or "")[
                :2000
            ]
        if "estado" in datos:
            c.estado = bool(datos.get("estado"))
        c.version_fila += 1
        c.save()
        _auditar(
            ctx,
            "EDITAR_CONCEPTO_CAJA",
            "Conceptos_movimiento",
            c.id_concepto_movimiento,
            nombre,
            self._audit,
        )
        item = next(
            x for x in self.listar_conceptos(None, "")["items"] if x["id_concepto_movimiento"] == pk
        )
        return {"mensaje": msg.MSG_CON_ACTUALIZADO, "item": item}

    def listar_cuentas_enmascaradas(self, **kwargs: Any) -> dict[str, Any]:
        data = AdminCajaService().listar(**kwargs)
        for it in data.get("items", []):
            it["numero"] = enmascarar_numero(it.get("numero") or "")
        return data

    # —— Jornada ——
    def _reporte_abierto(self, id_sede: int) -> Reportes_diarios:
        r = Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="ABIERTO").first()
        if not r:
            raise ReglaNegocioError(msg.MSG_JORNADA_AUSENTE, codigo="JORNADA_CERRADA")
        return r

    @transaction.atomic
    def apertura_jornada(
        self, ctx: AuthContext, id_sede: int, fecha: date | None = None
    ) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        dia = fecha or timezone.localdate()
        if Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="ABIERTO").exists():
            raise ReglaNegocioError(msg.MSG_JORNADA_YA_ABIERTA, codigo="VALIDACION")
        if Reportes_diarios.objects.filter(id_sede_id=id_sede, fecha=dia).exists():
            raise ReglaNegocioError(msg.MSG_JORNADA_FECHA, codigo="VALIDACION")
        ultimo = (
            Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="CERRADO")
            .order_by("-fecha")
            .first()
        )
        base = (
            ultimo.base_siguiente if ultimo and ultimo.base_siguiente is not None else Decimal("0")
        )
        r = Reportes_diarios.objects.create(
            id_sede_id=id_sede,
            fecha=dia,
            base_inicial=base,
            estado="ABIERTO",
            id_usuario_apertura_id=ctx.id_usuario,
        )
        _auditar(
            ctx,
            "APERTURA_JORNADA",
            "Reportes_diarios",
            r.id_reporte_diario,
            f"Sede {id_sede}",
            self._audit,
        )
        return {"mensaje": msg.MSG_JORNADA_ABIERTA, "reporte": _serializar_reporte(r)}

    @transaction.atomic
    def base_inicial_primera(self, ctx: AuthContext, id_sede: int, monto: Any) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        if Reportes_diarios.objects.filter(id_sede_id=id_sede).exists():
            raise ReglaNegocioError(msg.MSG_BASE_NO_PRIMERA, codigo="VALIDACION")
        valor = _dec(monto)
        r = Reportes_diarios.objects.create(
            id_sede_id=id_sede,
            fecha=timezone.localdate(),
            base_inicial=valor,
            estado="ABIERTO",
            id_usuario_apertura_id=ctx.id_usuario,
        )
        return {"mensaje": msg.MSG_BASE_INICIAL, "reporte": _serializar_reporte(r)}

    def jornada_actual(self, ctx: AuthContext, id_sede: int) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        r = Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="ABIERTO").first()
        if not r:
            return {"reporte": None, "mensaje": msg.MSG_JORNADA_AUSENTE}
        self._recalcular_totales(r)
        return {"reporte": _serializar_reporte(r), "mensaje": msg.MSG_JORNADA_ACTUAL}

    def _sum(self, model: type[_Model], reporte_id: int, campo: str = "valor") -> Decimal:
        agg = model.objects.filter(id_reporte_diario_id=reporte_id, anulado=False).aggregate(  # type: ignore[attr-defined]
            s=Sum(campo)
        )
        return agg["s"] or Decimal("0")

    @transaction.atomic
    def _recalcular_totales(self, r: Reportes_diarios) -> Reportes_diarios:
        r = Reportes_diarios.objects.select_for_update().get(pk=r.pk)
        r.total_gastos = self._sum(Gastos_caja, r.id_reporte_diario)
        r.total_ahorros = self._sum(Ahorros, r.id_reporte_diario)
        r.total_transferencias = self._sum(Transferencias_caja, r.id_reporte_diario)
        r.total_entregas = self._sum(Entregas_dinero, r.id_reporte_diario)
        r.base_adicional = Adiciones_base.objects.filter(
            id_reporte_diario_id=r.id_reporte_diario, anulado=False
        ).aggregate(s=Sum("valor"))["s"] or Decimal("0")
        ventas_pos = self._ventas.total_ventas_efectivo_jornada(r.id_sede_id, r.fecha)
        r.total_ventas = ventas_pos
        ventas_cuadre = r.venta_registrada if r.venta_registrada is not None else ventas_pos
        transf_manual = Transferencias_caja.objects.filter(
            id_reporte_diario_id=r.id_reporte_diario, anulado=False, origen="MANUAL"
        ).aggregate(s=Sum("valor"))["s"] or Decimal("0")
        r.efectivo_esperado = calcular_efectivo_esperado(
            r.base_inicial,
            r.base_adicional or Decimal("0"),
            ventas_cuadre,
            transf_manual,
            r.total_gastos,
            r.total_ahorros,
            r.total_entregas,
            variante=VarianteCalculoEfectivo.VARIANTE_B,
        )
        r.save(
            update_fields=[
                "total_gastos",
                "total_ahorros",
                "total_transferencias",
                "total_entregas",
                "base_adicional",
                "total_ventas",
                "efectivo_esperado",
            ]
        )
        return r

    def cuadre_tiempo_real(self, ctx: AuthContext, id_sede: int) -> dict[str, Any]:
        r = self._reporte_abierto(id_sede)
        _assert_sede(ctx, id_sede)
        r = self._recalcular_totales(r)
        return {"mensaje": msg.MSG_CUADRE, "reporte": _serializar_reporte(r)}

    def _categoria_tipo(self, id_categoria: int, tipo: str) -> Categorias_movimiento:
        c = Categorias_movimiento.objects.filter(
            pk=id_categoria, estado=True, tipo_movimiento=tipo
        ).first()
        if not c:
            raise ReglaNegocioError(msg.MSG_CATEGORIA_TIPO, codigo="VALIDACION")
        return c

    @transaction.atomic
    def registrar_gasto_o_ahorro(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        id_sede = int(datos.get("id_sede") or 0)
        _assert_sede(ctx, id_sede)
        r = self._reporte_abierto(id_sede)
        tipo = (datos.get("tipo") or "gasto").strip().lower()
        if tipo not in {"gasto", "ahorro"}:
            raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION")
        cat_tipo = "Gasto" if tipo == "gasto" else "Ahorro"
        cat = self._categoria_tipo(int(datos.get("id_categoria") or 0), cat_tipo)
        valor = _dec(datos.get("valor"))
        desc = (datos.get("descripcion") or "").strip() or cat.nombre
        id_concepto = int(datos["id_concepto"]) if datos.get("id_concepto") else None
        modelo = Gastos_caja if tipo == "gasto" else Ahorros
        row = modelo.objects.create(
            id_reporte_diario=r,
            id_categoria=cat,
            id_concepto_id=id_concepto,
            valor=valor,
            descripcion=desc,
            id_usuario_id=ctx.id_usuario,
        )
        self._recalcular_totales(r)
        _auditar(ctx, f"REGISTRAR_{tipo.upper()}", modelo.__name__, row.pk, desc, self._audit)
        return {"mensaje": msg.MSG_MOV_REGISTRADO, "id": row.pk, "tipo": tipo}

    def listar_gastos_ahorros(self, ctx: AuthContext, id_sede: int) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        r = Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="ABIERTO").first()
        if not r:
            return {"gastos": [], "ahorros": [], "mensaje": msg.MSG_JORNADA_AUSENTE}

        def _rows(model: type[_Model], tipo: str) -> list[dict[str, Any]]:
            return [
                {
                    "id": row.pk,
                    "tipo": tipo,
                    "valor": str(row.valor),
                    "descripcion": row.descripcion,
                    "anulado": row.anulado,
                    "fecha_hora": row.fecha_hora.isoformat(),
                }
                for row in model.objects.filter(id_reporte_diario=r).order_by("-fecha_hora")  # type: ignore[attr-defined]
            ]

        return {
            "gastos": _rows(Gastos_caja, "gasto"),
            "ahorros": _rows(Ahorros, "ahorro"),
            "mensaje": msg.MSG_MOV_LISTADO,
        }

    @transaction.atomic
    def registrar_transferencia(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        id_sede = int(datos.get("id_sede") or 0)
        _assert_sede(ctx, id_sede)
        r = self._reporte_abierto(id_sede)
        cat = self._categoria_tipo(int(datos.get("id_categoria") or 0), "Transferencia")
        cuenta = AdminCajaService().cuenta_activa(int(datos.get("id_cuenta_bancaria") or 0))
        valor = _dec(datos.get("valor"))
        ref = (datos.get("referencia") or "").strip()
        if not ref:
            raise ReglaNegocioError(msg.MSG_REFERENCIA, codigo="VALIDACION")
        t = Transferencias_caja.objects.create(
            id_reporte_diario=r,
            id_categoria=cat,
            id_cuenta_bancaria=cuenta,
            valor=valor,
            referencia=ref[:100],
            observaciones=str(datos.get("observaciones") or "")[:255],
            origen="MANUAL",
            editable=True,
            id_usuario_id=ctx.id_usuario,
        )
        self._recalcular_totales(r)
        _auditar(
            ctx,
            "REGISTRAR_TRANSFERENCIA",
            "Transferencias_caja",
            t.id_transferencia,
            ref,
            self._audit,
        )
        return {"mensaje": msg.MSG_TRANSFERENCIA, "id_transferencia": t.id_transferencia}

    def listar_transferencias(self, ctx: AuthContext, id_sede: int) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        r = Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="ABIERTO").first()
        if not r:
            return {"items": [], "mensaje": msg.MSG_JORNADA_AUSENTE}
        items = [
            {
                "id_transferencia": t.id_transferencia,
                "valor": str(t.valor),
                "referencia": t.referencia,
                "origen": t.origen,
                "editable": t.editable,
                "anulado": t.anulado,
                "id_cuenta_bancaria": t.id_cuenta_bancaria_id,
            }
            for t in Transferencias_caja.objects.filter(id_reporte_diario=r).order_by("-fecha_hora")
        ]
        return {"items": items, "mensaje": msg.MSG_MOV_LISTADO}

    @transaction.atomic
    def registrar_adicion(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        id_sede = int(datos.get("id_sede") or 0)
        _assert_sede(ctx, id_sede)
        r = self._reporte_abierto(id_sede)
        a = Adiciones_base.objects.create(
            id_reporte_diario=r,
            valor=_dec(datos.get("valor")),
            motivo=str(datos.get("motivo") or "Adición de base")[:255],
            id_usuario_id=ctx.id_usuario,
        )
        self._recalcular_totales(r)
        return {"mensaje": msg.MSG_ADICION, "id_adicion": a.id_adicion}

    @transaction.atomic
    def registrar_entrega(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        id_sede = int(datos.get("id_sede") or 0)
        _assert_sede(ctx, id_sede)
        r = self._reporte_abierto(id_sede)
        valor = _dec(datos.get("valor"), positivo=False)
        if valor < 0:
            raise ReglaNegocioError(msg.MSG_ENTREGA_NEG, codigo="VALIDACION")
        e = Entregas_dinero.objects.create(
            id_reporte_diario=r,
            valor=valor,
            descripcion=str(datos.get("descripcion") or "")[:255],
            id_usuario_id=ctx.id_usuario,
        )
        self._recalcular_totales(r)
        return {"mensaje": msg.MSG_ENTREGA, "id_entrega": e.id_entrega}

    @transaction.atomic
    def corregir_movimiento(
        self, ctx: AuthContext, tipo: str, pk: int, datos: dict[str, Any]
    ) -> dict[str, Any]:
        tipo = tipo.strip().lower()
        row: Gastos_caja | Ahorros | Transferencias_caja | None
        if tipo == "gasto":
            row = Gastos_caja.objects.select_for_update().filter(pk=pk).first()
        elif tipo == "ahorro":
            row = Ahorros.objects.select_for_update().filter(pk=pk).first()
        elif tipo == "transferencia":
            row = Transferencias_caja.objects.select_for_update().filter(pk=pk).first()
            if row and not row.editable and row.origen == "VENTA":
                raise ReglaNegocioError(
                    msg.MSG_TRANSFERENCIA_FACTURADA, codigo="TRANSFERENCIA_FACTURADA"
                )
        else:
            raise ReglaNegocioError(msg.MSG_VALIDACION, codigo="VALIDACION")
        if not row:
            raise ReglaNegocioError(msg.MSG_NO_ENCONTRADO, codigo="NO_ENCONTRADO")
        rep = row.id_reporte_diario
        if rep.estado != "ABIERTO":
            raise ReglaNegocioError(msg.MSG_JORNADA_CERRADA, codigo="JORNADA_CERRADA")
        _assert_sede(ctx, rep.id_sede_id)
        if int(datos.get("version_fila") or 0) != row.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        if "valor" in datos and hasattr(row, "valor"):
            row.valor = _dec(datos["valor"])
        if "descripcion" in datos and hasattr(row, "descripcion"):
            row.descripcion = str(datos["descripcion"])[:2000]
        if "anulado" in datos:
            row.anulado = bool(datos.get("anulado"))
            row.motivo_anulacion = str(datos.get("motivo_anulacion") or "")[:255]
        row.version_fila += 1
        row.save()
        self._recalcular_totales(rep)
        return {"mensaje": msg.MSG_CORREGIDO}

    def registrar_adjunto_stub(self, ctx: AuthContext, datos: dict[str, Any]) -> dict[str, Any]:
        nombre = (datos.get("nombre_original") or "soporte.pdf")[:255]
        return {"mensaje": msg.MSG_ADJUNTO_STUB, "nombre_original": nombre, "pendiente": True}

    @transaction.atomic
    def actualizar_venta_registrada(
        self, ctx: AuthContext, id_sede: int, datos: dict[str, Any]
    ) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        r = self._reporte_abierto(id_sede)
        if int(datos.get("version_fila") or 0) != r.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        if "venta_registrada" in datos:
            raw = datos.get("venta_registrada")
            r.venta_registrada = _dec(raw, positivo=False) if raw not in (None, "") else None
        self._recalcular_totales(r)
        return {"mensaje": msg.MSG_VENTA_REGISTRADA, "reporte": _serializar_reporte(r)}

    @transaction.atomic
    def cierre_jornada(
        self, ctx: AuthContext, id_sede: int, datos: dict[str, Any]
    ) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        r = self._reporte_abierto(id_sede)
        if int(datos.get("version_fila") or 0) != r.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        r = self._recalcular_totales(r)
        declarado = _dec(datos.get("efectivo_declarado"), positivo=False)
        r.efectivo_declarado = declarado
        r.diferencia = declarado - (r.efectivo_esperado or Decimal("0"))
        r.base_siguiente = datos.get("base_siguiente")
        if r.base_siguiente not in (None, ""):
            r.base_siguiente = _dec(r.base_siguiente, positivo=False)
        r.observaciones_cierre = str(
            datos.get("observaciones") or datos.get("observaciones_cierre") or ""
        )[:5000]
        r.estado = "CERRADO"
        r.fecha_cierre = timezone.now()
        r.id_usuario_cierre_id = ctx.id_usuario
        r.version_fila += 1
        r.save()
        _auditar(
            ctx, "CIERRE_JORNADA", "Reportes_diarios", r.id_reporte_diario, "Cierre", self._audit
        )
        return {"mensaje": msg.MSG_CIERRE, "reporte": _serializar_reporte(r)}

    @transaction.atomic
    def reapertura_jornada(
        self, ctx: AuthContext, id_sede: int, datos: dict[str, Any]
    ) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        if Reportes_diarios.objects.filter(id_sede_id=id_sede, estado="ABIERTO").exists():
            raise ReglaNegocioError(msg.MSG_JORNADA_YA_ABIERTA, codigo="VALIDACION")
        id_reporte = int(datos.get("id_reporte_diario") or 0)
        r = (
            Reportes_diarios.objects.select_for_update()
            .filter(pk=id_reporte, id_sede_id=id_sede)
            .first()
        )
        if not r or r.estado != "CERRADO":
            raise ReglaNegocioError(msg.MSG_NO_ENCONTRADO, codigo="NO_ENCONTRADO")
        if int(datos.get("version_fila") or 0) != r.version_fila:
            raise ReglaNegocioError(MSG_CONCURRENCIA, codigo="CONCURRENCIA")
        r.estado = "ABIERTO"
        r.fecha_cierre = None
        r.id_usuario_cierre_id = None
        r.efectivo_declarado = None
        r.diferencia = None
        r.version_fila += 1
        r.save()
        _auditar(
            ctx,
            "REAPERTURA_JORNADA",
            "Reportes_diarios",
            r.id_reporte_diario,
            "Reapertura",
            self._audit,
        )
        return {"mensaje": msg.MSG_REAPERTURA, "reporte": _serializar_reporte(r)}

    def historial(
        self, ctx: AuthContext, id_sede: int, desde: str | None, hasta: str | None
    ) -> dict[str, Any]:
        _assert_sede(ctx, id_sede)
        qs = Reportes_diarios.objects.filter(id_sede_id=id_sede).order_by("-fecha")
        if desde:
            qs = qs.filter(fecha__gte=desde)
        if hasta:
            qs = qs.filter(fecha__lte=hasta)
        items = [_serializar_reporte(r) for r in qs[:60]]
        return {"items": items, "mensaje": msg.MSG_HISTORIAL.format(n=len(items))}

    def exportar_historial(
        self, ctx: AuthContext, id_sede: int, formato: str
    ) -> tuple[str, bytes, str]:
        data = self.historial(ctx, id_sede, None, None)
        if not data["items"]:
            raise ReglaNegocioError(msg.MSG_HISTORIAL_VACIO, codigo="EXPORT_VACIO")
        nombre = f"caja-historial-sede-{id_sede}.csv"
        buff = io.StringIO()
        writer = csv.DictWriter(buff, fieldnames=list(data["items"][0].keys()))
        writer.writeheader()
        writer.writerows(data["items"])
        contenido = buff.getvalue().encode("utf-8-sig")
        mime = "text/csv"
        if (formato or "").lower() == "xlsx":
            try:
                from openpyxl import Workbook  # type: ignore[import-untyped]

                wb = Workbook()
                ws = wb.active
                ws.title = "historial"
                headers = list(data["items"][0].keys())
                ws.append(headers)
                for row in data["items"]:
                    ws.append([row.get(h) for h in headers])
                out = io.BytesIO()
                wb.save(out)
                contenido = out.getvalue()
                nombre = nombre.replace(".csv", ".xlsx")
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            except ImportError:
                pass
        return nombre, contenido, mime
