# ==============================================================================
# Prueba de Concurrencia: Un Solo Ganador en Edición Simultánea - MPDW
# SAD Ref: ADR-005, QA-11, Regla R3
# ==============================================================================
import concurrent.futures
from decimal import Decimal

import pytest

from apps.m01_identidad.models import Roles, Usuario_sede, Usuarios
from apps.m02_sedes.models import Sedes
from apps.m03_catalogo.models import Categorias_producto, Productos
from apps.m03_catalogo.repositories import ProductoRepository
from apps.m03_catalogo.services import ProductoService
from apps.m10_auditoria.services import AuditService
from apps.m13_plataforma.gestor_transaccion import GestorTransaccionDjango
from contratos.dtos import AuthContext
from contratos.excepciones import ConflictoVersionError


@pytest.mark.django_db(transaction=True)
@pytest.mark.concurrency
def test_exactamente_un_ganador_ante_50_actualizaciones_concurrentes_con_misma_version():
    """
    Escenario QA-11: 50 hilos concurrentes intentan cambiar el precio del mismo producto
    partiendo exactamente de la misma versión (v1).
    Resultado esperado: Exactamente 1 hilo tiene éxito (v1 -> v2) y 49 hilos reciben
    ConflictoVersionError (HTTP 409).
    """
    sede, _ = Sedes.objects.get_or_create(nombre="Sede Concurrencia", defaults={"direccion": "Carrera 50"})
    rol, _ = Roles.objects.get_or_create(nombre="Administrador", defaults={"es_rol_base": True})
    user = Usuarios.objects.create_user(email="admin_conc@mpdw.com", password="Password123!", nombre="Admin", documento="999888", id_rol=rol)
    Usuario_sede.objects.create(id_usuario=user, id_sede=sede, es_principal=True)

    cat = Categorias_producto.objects.create(nombre="Pinturas Epoxicas")
    producto = Productos.objects.create(
        codigo_producto="EPOX-01",
        nombre="Pintura Epoxica Alto Trafico",
        precio_venta=Decimal("80000.00"),
        id_categoria=cat,
        version=1,
    )

    ctx = AuthContext(
        id_usuario=user.id_usuario,
        email=user.email,
        rol_nombre=rol.nombre,
        sedes_asignadas=(sede.id_sede,),
        es_global=True,
    )

    service = ProductoService(
        producto_repo=ProductoRepository(),
        audit_port=AuditService(),
        tx_manager=GestorTransaccionDjango(),
    )

    exitos = 0
    conflictos_409 = 0

    def intentar_cambio_precio(indice: int) -> bool:
        try:
            service.cambiar_precio(
                ctx=ctx,
                id_producto=producto.id_producto,
                nuevo_precio=Decimal("85000.00") + Decimal(indice),
                version=1,  # Todos parten compitiendo por la versión 1
                motivo=f"Actualizacion concurrente desde hilo {indice}",
            )
            return True
        except ConflictoVersionError:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(intentar_cambio_precio, i) for i in range(50)]
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                exitos += 1
            else:
                conflictos_409 += 1

    producto.refresh_from_db()

    # Verificaciones finales
    assert exitos == 1, f"Se esperaba exactamente 1 ganador, pero hubo {exitos}"
    assert conflictos_409 == 49, f"Se esperaban 49 conflictos 409, pero hubo {conflictos_409}"
    assert producto.version == 2, f"La versión final del producto en BD debe ser 2, pero es {producto.version}"

