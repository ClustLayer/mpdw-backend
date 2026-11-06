# Mundo Pinturas Diana Web (MPDW) - Backend & ETL

[![CI](https://github.com/ClustLayer/mpdw-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/ClustLayer/mpdw-backend/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2%20LTS-092E20)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-Privada-red)](LICENSE)

**Versión del producto:** 1.1.5 (Sprint 1 — cierre Épicas 13 y 18; épicas anteriores 1.1.1–1.1.4).

Repositorio oficial del backend y proceso de analítica por lotes (ETL) de **Mundo Pinturas Diana Web (MPDW)**. Diseñado con una arquitectura por capas modularizada por dominio (Aplicación → Negocio → Persistencia) sobre **Python 3.13**, **Django 5.2 LTS**, **Django REST Framework** y **PostgreSQL 16 en Supabase**, garantizando fronteras transaccionales atómicas locales (`transaction.atomic`), control de concurrencia optimista (`version` con HTTP 409), bloqueo acotado de filas, auditoría transaccional inmutable (`Auditoria`) y exclusión estricta de componentes no contemplados (sin DIAN, sin Celery, sin Redis, sin dependencias a Supabase en el cliente).

---

## 1. Requisitos Previos

* **Docker:** Versión ≥ 24.0 (probado con Docker 29.8 / Desktop)
* **Docker Compose:** Versión ≥ 2.20
* **uv:** Versión 0.13.6 (fijada y verificada a oct-2026, SAD C-13)
* **Python:** 3.13.18 (CPython 3.13 LTS fijado en `.python-version` y Dockerfile)
* **PostgreSQL Client (psql):** 16.x (PostgreSQL 16.6 en Supabase / Docker)

---

## 2. Inicio Rápido con Docker Compose (Quickstart)

### Paso 1: Clonar y configurar variables de entorno
```bash
git clone https://github.com/mundopinturasdiana/mpdw-backend.git
cd mpdw-backend
cp .env.example .env
```

### Paso 2: Construir e iniciar contenedores
```bash
docker compose up --build -d
```
*El servicio `api` esperará a que el contenedor `db` supere su verificación de salud (`healthcheck`).*

### Paso 3: Aplicar migraciones, crear el administrador inicial y arrancar
```bash
# Aplicar migraciones de Django
docker compose exec api python manage.py migrate

# Crear tabla de caché en base de datos para límites de tasa (throttling)
docker compose exec api python manage.py createcachetable

# Crear el administrador inicial y roles base (SAD BR-09, D6)
docker compose exec api python manage.py create_initial_admin
```

---

## 3. Secuencia de Verificación Funcional del Slice Vertical (cURL y PowerShell)

Flujo transaccional completo de referencia (Regla R2) que atraviesa todas las capas de la arquitectura: autenticación JWT → creación de producto con inventario inicial y auditoría (TX-07) → actualización de precio con control optimista (TX-06, TX-11) → demostración de **HTTP 409 Conflict** ante colisión de versión.

### Opción A: Comandos en Bash (Linux / macOS / Git Bash / WSL)
```bash
# 1. Iniciar sesión como Administrador (obtiene access token y almacena cookie HttpOnly en cookies.txt)
TOKEN=$(curl -s -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{"email":"admin@mundopinturasdiana.com","password":"AdminSeguro2026!"}' \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Access Token obtenido: $TOKEN"

# 2. Dar de alta un producto con inventario inicial en Sede 1 (TX-07)
curl -i -X POST http://localhost:8000/api/v1/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_producto": "VINIL-PREM-01",
    "nombre": "Vinilo Premium Blanco 5 Galones",
    "precio_venta": "125000.00",
    "id_categoria": 1,
    "stocks_iniciales": [
      {"id_sede": 1, "cantidad_inicial": "30.00"}
    ]
  }'
# Nota: La respuesta retornará HTTP 201 Created con cabecera ETag: W/"1"

# 3. Cambiar el precio con motivo obligatorio y versión vigente v1 (TX-06, TX-11)
curl -i -X PATCH http://localhost:8000/api/v1/products/1/price \
  -H "Authorization: Bearer $TOKEN" \
  -H "If-Match: W/\"1\"" \
  -H "Content-Type: application/json" \
  -d '{
    "nuevo_precio": "132000.00",
    "motivo": "Incremento de costo de materia prima resina",
    "version": 1
  }'
# Nota: Respuesta HTTP 200 OK con nuevo precio y nueva cabecera ETag: W/"2"

# 4. Intentar actualizar nuevamente con la versión desactualizada v1 (Provocar HTTP 409)
curl -i -X PATCH http://localhost:8000/api/v1/products/1/price \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nuevo_precio": "140000.00",
    "motivo": "Actualizacion concurrente no sincronizada",
    "version": 1
  }'
# Resultado esperado: HTTP 409 Conflict con cuerpo uniforme {codigo: "CONFLICTO_CONCURRENCIA", ...}
```

### Opción B: Comandos en Windows PowerShell
```powershell
# 1. Iniciar sesión como Administrador y guardar cookies
$loginRes = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -ContentType "application/json" -Body '{"email":"admin@mundopinturasdiana.com","password":"AdminSeguro2026!"}' -SessionVariable sess
$TOKEN = $loginRes.access_token
Write-Host "Access Token obtenido: $TOKEN"

# 2. Dar de alta un producto con inventario inicial en Sede 1
$prodBody = '{"codigo_producto":"VINIL-PREM-01","nombre":"Vinilo Premium Blanco 5 Galones","precio_venta":"125000.00","id_categoria":1,"stocks_iniciales":[{"id_sede":1,"cantidad_inicial":"30.00"}]}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/products/" -Method Post -ContentType "application/json" -Headers @{"Authorization"="Bearer $TOKEN"} -Body $prodBody

# 3. Cambiar el precio con versión vigente v1 (éxito)
$priceBody = '{"nuevo_precio":"132000.00","motivo":"Incremento de materia prima","version":1}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/products/1/price" -Method Patch -ContentType "application/json" -Headers @{"Authorization"="Bearer $TOKEN"; "If-Match"='W/"1"'} -Body $priceBody

# 4. Intentar actualizar nuevamente con versión vieja v1 (HTTP 409)
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/products/1/price" -Method Patch -ContentType "application/json" -Headers @{"Authorization"="Bearer $TOKEN"} -Body '{"nuevo_precio":"140000.00","motivo":"Reintento desactualizado","version":1}'
} catch {
    Write-Host "Capturado error esperado:" $_.Exception.Response.StatusCode.value__
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    Write-Host $reader.ReadToEnd()
}
```

---

## 4. Desarrollo Local sin Docker (con uv)

```bash
# 1. Instalar dependencias congeladas
uv sync

# 2. Configurar base de datos local y aplicar migraciones
export DJANGO_SETTINGS_MODULE=config.settings.development
uv run python manage.py migrate
uv run python manage.py createcachetable
uv run python manage.py create_initial_admin

# 3. Iniciar servidor de desarrollo
uv run python manage.py runserver 0.0.0.0:8000
```

---

## 5. Estrategia de Pruebas y Cobertura (Regla R3)

El arquetipo implementa una suite de pruebas multi-nivel:
* **Pruebas Unitarias:** Sin base de datos ni I/O, evaluando la capa de Negocio pura con fakes en memoria. Gate del **100% de cobertura en líneas y ramas**.
* **Pruebas de Integración:** Contra base de datos PostgreSQL real, validando triggers de inmutabilidad, aislamiento de sede y control optimista.
* **Pruebas de Concurrencia:** Con 50 hilos en paralelo sobre base transaccional (`transactional_db`), validando exactamente un ganador ante colisiones de versión (QA-11).

```bash
# Ejecutar pruebas unitarias con gate de cobertura del 100% en capa de Negocio
uv run pytest tests/unit -m unit --cov=apps --cov-report=term-missing --cov-report=html

# Ver reporte HTML de cobertura
open htmlcov/index.html  # o start htmlcov/index.html en Windows

# Ejecutar pruebas de integración
uv run pytest tests/integration -m integration

# Ejecutar pruebas de concurrencia (QA-11)
uv run pytest tests/concurrency -m concurrency

# Ejecutar suite completa
uv run pytest
```

---

## 6. Puertas de Calidad en CI/CD (Quality Gates)

Comandos para reproducir localmente las puertas del pipeline de GitHub Actions (`.github/workflows/ci.yml`):

```bash
# Linter y estilo
uv run ruff check .

# Verificación de tipos estáticos
uv run mypy apps contratos config etl

# Verificación de contratos arquitectónicos entre capas y módulos
uv run lint-imports

# Análisis estático de seguridad (SAST)
uv run bandit -r apps config etl contratos -x tests

# Auditoría de vulnerabilidades en dependencias
uv run pip-audit

# Comprobación de integridad del contrato OpenAPI
uv run python manage.py spectacular --file /tmp/openapi_check.yaml
diff -u docs/openapi.yaml /tmp/openapi_check.yaml
```

---

## 7. Ejecución del Proceso ETL de Analítica

El comando de gestión `run_etl` realiza la agregación periódica por lotes hacia el esquema `analitica` bajo exclusión mutua mediante `pg_try_advisory_xact_lock` (SAD ADR-013):

```bash
# Ejecutar corrida normal (últimos 7 días)
docker compose exec api python manage.py run_etl

# Ejecutar reprocesamiento histórico acotado
docker compose exec api python manage.py run_etl --desde 2026-10-01 --hasta 2026-10-30

# Ejecutar como servicio one-shot en compose
docker compose --profile etl run --rm etl
```

---

## 8. Matriz de Trazabilidad Arquitectónica (SAD ID → Archivo)

| SAD ID | Descripción / Decisión | Archivo(s) en Repositorio |
| :--- | :--- | :--- |
| **ADR-001** | Arquitectura por capas, módulos por dominio y dos repositorios | `config/settings/base.py`, `apps/*/`, `contratos/` |
| **ADR-003** | PostgreSQL único en Supabase, pooler transaction mode (6543) | `config/settings/base.py` (`DISABLE_SERVER_SIDE_CURSORS`, `prepare_threshold=None`) |
| **ADR-004** | Python + Django REST Framework con uv | `pyproject.toml`, `uv.lock`, `Dockerfile` |
| **ADR-005** | Transacciones atómicas, bloqueos acotados y concurrencia optimista | `contratos/puertos/transaccion.py`, `apps/m03_catalogo/repositories.py` |
| **ADR-006** | JWT acceso corto + refresh opaco rotado en cookie HttpOnly | `apps/m01_identidad/services.py`, `views.py`, `authentication.py` |
| **ADR-007** | Autorización en servidor con alcance por sede en repositorios | `apps/m01_identidad/permissions.py`, `repositories.py` |
| **ADR-008** | Auditoría transaccional e inmutable en base de datos | `apps/m10_auditoria/models.py`, `services.py`, `migrations/0001_initial.py` |
| **ADR-009** | Facturación electrónica: solo registro local, sin integración DIAN | `apps/m06_ventas/models.py` (`Facturas_electronicas`) |
| **ADR-010** | Un solo proceso diferido (ETL en Cron), sin Celery ni Redis | `etl/management/commands/run_etl.py`, `apps/m13_plataforma/throttling.py` |
| **ADR-011** | Supabase Storage (bucket público y privado) | `contratos/puertos/almacenamiento.py` |
| **ADR-012** | Despliegue en Render, Supabase y Vercel | `Dockerfile`, `docker-compose.yml`, `config/settings/production.py` |
| **ADR-013** | Agregación ETL con advisory xact lock hacia esquema analitica | `etl/management/commands/run_etl.py`, `etl/migrations/0001_initial.py` |
| **BR-01, C-04** | Cuadre de caja parametrizado (Variante A y B, [Pendiente Q-02]) | `apps/m08_caja/dominio.py`, `tests/unit/test_money_calculator.py` |
| **BR-08, BR-09** | Prohibición de autorregistro público; eliminación lógica | `apps/m01_identidad/models.py`, `create_initial_admin.py` |
| **BR-10** | RBAC híbrido (override individual -> rol base -> denegar) | `apps/m01_identidad/repositories.py` (`PermissionRepository`) |
| **G-08** | Columna version para control optimista (HTTP 409) | `apps/m03_catalogo/models.py` (`Productos.version`) |
| **G-01, G-03** | Stubs desacoplados sin tabla física (`managed = False`) | `apps/m12_tienda_publica/models.py`, `apps/m06_ventas/models.py` |
| **G-14, RI-16** | Estructura Auditoria (JSONB, correlación) y trigger anti-modificación | `apps/m10_auditoria/migrations/0001_initial.py` |
| **IX-1** | Búsqueda rápida por nombre/código con trigramas pg_trgm | `apps/m03_catalogo/models.py` (`GinIndex gin_trgm_ops`) |
| **§9.1** | Cuerpo uniforme de error `{codigo, mensaje, detalles, idCorrelacion}` | `apps/m13_plataforma/excepciones.py` |

---

## 9. Alcance de Tablas Físicas y Modelos

El arquetipo implementa las entidades de los módulos en alcance funcional del backend y del slice vertical:
* **M01 Identidad:** `Usuarios`, `Roles`, `Permisos`, `Rol_permiso`, `Usuario_permiso`, `Usuario_sede`.
* **M02 Sedes:** `Sedes`.
* **M03 Catálogo:** `Productos`, `Categorias_producto`, `Marcas`, `Tipos_producto`, `Historial_precios`.
* **M04 Inventario:** `Inventarios`, `Movimientos_inventario`.
* **M05 Clientes:** `Clientes`.
* **M06 Ventas:** `Facturas`, `Lineas_factura`, `Facturas_electronicas` (y `Consecutivos` como stub `managed = False` sin tabla física, G-03).
* **M07 Domicilios:** `Domicilios`, `Estados_domicilio`.
* **M08 Caja:** `Cierres_caja`.
* **M10 Auditoría:** `Auditoria` (con trigger inmutable RI-16).
* **M12 Tienda Pública:** `Pedidos_web` (como stub `managed = False` sin tabla física, G-01).
* **M13 Plataforma:** `django_cache` (tabla de base de datos para límites de tasa y throttling ADR-010).
* **ETL Analítica:** Esquema `analitica` (`ventas_diarias`, `movimientos_diarios`, `productos_top`, `inventario_alerta`).

---

## 10. Limitaciones Conocidas y Próximos Pasos

1. **Prueba contra Pooler en Staging (R-25):** Antes del despliegue productivo, debe ejecutarse una prueba de integración contra el pooler real de Supabase en modo transacción (`port 6543`) para revalidar el comportamiento de `select_for_update` y deshabilitación de cursores del servidor (`DISABLE_SERVER_SIDE_CURSORS = True`).
2. **Definiciones de Negocio Abiertas:**
   - **C-04 / Q-02 (Fórmula de Caja):** `apps/m08_caja/dominio.py` implementa `calcular_efectivo_esperado` parametrizada con `VarianteCalculoEfectivo.VARIANTE_A` y `VARIANTE_B` (marcada como `[Pendiente Q-02]` a la espera de decisión gerencial).
   - **C-02 (Cálculo de Descuentos):** Requiere definición formal de reglas comerciales antes del Sprint 2.
   - **C-03 (Política de Devoluciones y Notas Crédito):** Requiere definición de impacto en inventario físico vs financiero.
   - **Q-05 (Tiempo de Expiración de Sesión):** Access token fijado a 15 min y refresh a 7 días según SAD §8.3, sujeto a confirmación de seguridad.
   - **Q-21 (Reglas de Bloqueo de Stock en Checkout):** Pendiente de definición de TTL de reserva temporal.
3. **Frontend Inexistente / R-23 y Q-22 Diferidos:** Actualmente no existe frontend conectado. Los repositorios de demostración quedan descartados y no forman parte del proyecto. R-23 y Q-22 se marcan formalmente como **DIFERIDOS: sin frontend por ahora**. La especificación `docs/openapi.yaml` queda como **draft v1**.
4. **Mecanismos de Navegador Probados por HTTP:** Los mecanismos de seguridad de navegador (cookie `SameSite=Strict`, validación de `Origin`, CORS con lista blanca y endpoints SEO públicos) se validan mediante peticiones HTTP directas con cURL y PowerShell. Quedan limitados a verificación sin navegador real hasta que exista un cliente web operativo.
5. **Módulos M05–M09, M11, M12 en estado Stub:** Sus servicios de dominio, modelos y contratos de puertos están testeados al 100% de cobertura y preparados para recibir la lógica de negocio en sus sprints correspondientes.
6. **Workflow de Despliegue y Migración:** El servicio one-shot `migrate` en Docker Compose y el pipeline de CI/CD validan la preparación para despliegue; la ejecución del pipeline completo de producción en Render y Supabase se concretará al aprovisionar los ambientes definitivos.

