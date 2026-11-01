# ==============================================================================
# Repositorio de Catálogo y Concurrencia Optimista - MPDW
# SAD Ref: M03, ADR-005, G-08, IX-1
# ==============================================================================
from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone

from apps.m03_catalogo.models import Historial_precios, Productos


class ProductoRepository:
    """Persistencia de Productos y control de concurrencia optimista."""

    def buscar_por_id(self, id_producto: int) -> Productos | None:
        try:
            return Productos.objects.select_related("id_categoria", "id_marca", "id_tipo_producto").get(pk=id_producto)
        except Productos.DoesNotExist:
            return None

    def buscar_por_codigo(self, codigo: str) -> Productos | None:
        return Productos.objects.filter(codigo_producto__iexact=codigo).first()

    def crear_producto(
        self,
        codigo_producto: str,
        nombre: str,
        precio_venta: Decimal,
        id_categoria_id: int,
        codigo_barras: str | None = None,
        descripcion: str = "",
        id_marca_id: int | None = None,
        id_tipo_producto_id: int | None = None,
        inventario_habilitado: bool = True,
    ) -> Productos:
        return Productos.objects.create(
            codigo_producto=codigo_producto,
            codigo_barras=codigo_barras,
            nombre=nombre,
            descripcion=descripcion,
            precio_venta=precio_venta,
            id_categoria_id=id_categoria_id,
            id_marca_id=id_marca_id,
            id_tipo_producto_id=id_tipo_producto_id,
            inventario_habilitado=inventario_habilitado,
            version=1,
            estado=True,
        )

    def actualizar_precio_concurrente(
        self,
        id_producto: int,
        nuevo_precio: Decimal,
        version_esperada: int,
    ) -> int:
        """
        Ejecuta la actualización condicional atómica (SAD ADR-005):
        UPDATE "Productos" SET precio_venta = :nuevo, version = version + 1
        WHERE id_producto = :id AND version = :version_esperada;
        Retorna el número de filas modificadas (1 si tuvo éxito, 0 si hay conflicto 409).
        """
        filas_afectadas = Productos.objects.filter(
            pk=id_producto,
            version=version_esperada,
        ).update(
            precio_venta=nuevo_precio,
            version=F("version") + 1,
        )
        return filas_afectadas

    def listar_con_filtro(self, termino: str | None = None, id_categoria: int | None = None):
        qs = Productos.objects.filter(estado=True).select_related("id_categoria", "id_marca", "id_tipo_producto")
        if id_categoria:
            qs = qs.filter(id_categoria_id=id_categoria)
        if termino:
            # IX-1: Búsqueda flexible por código, código de barras o nombre
            qs = qs.filter(
                Q(codigo_producto__icontains=termino)
                | Q(codigo_barras__icontains=termino)
                | Q(nombre__icontains=termino)
            )
        return qs.order_by("nombre")


class HistorialPreciosRepository:
    """Manejo de registros de vigencia de precios."""

    def cerrar_precio_vigente(self, id_producto: int) -> None:
        Historial_precios.objects.filter(
            id_producto_id=id_producto,
            fecha_fin__isnull=True,
        ).update(fecha_fin=timezone.now())

    def registrar_nuevo_precio(
        self,
        id_producto: int,
        precio_anterior: Decimal,
        precio_nuevo: Decimal,
        motivo: str,
        id_usuario: int | None = None,
    ) -> Historial_precios:
        return Historial_precios.objects.create(
            id_producto_id=id_producto,
            precio_anterior=precio_anterior,
            precio_nuevo=precio_nuevo,
            motivo=motivo,
            id_usuario_id=id_usuario,
            fecha_fin=None,
        )

