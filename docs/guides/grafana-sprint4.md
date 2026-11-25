# Observabilidad Sprint 4 — logs, interacciones y Grafana

Este documento combina:
1. Los requisitos de **HU_S4_02 / HU_S4_03 / HU_S4_04** (MongoDB Atlas + paneles).
2. El **informe técnico de centralización de logs** (stdout → Fluent Bit → Loki → Grafana → archivo bimestral en Object Storage).

## Principios (informe)

- Frontend y backend emiten eventos a **stdout/stderr** (JSON preferible); no dependen de archivos locales permanentes.
- Un agente (**Fluent Bit**) recolecta, etiqueta (`service`, `environment`, `host`) y envía al almacén de consulta (**Loki**).
- **Grafana** visualiza Loki (y, en este sprint, también MongoDB).
- **Backup ≠ borrado**: exportar → verificar checksum/lectura → aplicar retención. Archivo bimestral en Object Storage (S3/R2/MinIO).
- Nunca registrar contraseñas, tokens, `Authorization` ni datos personales innecesarios.

## Capas en MPDW

| Capa | Destino | Uso |
|------|---------|-----|
| Bitácora de seguridad SQL | PostgreSQL `Auditoria` | Solo `LOGIN_EXITOSO`, `LOGIN_FALLIDO`, `CAMBIO_PASSWORD` |
| Logs de negocio / HTTP | MongoDB `MONGODB_GENERAL_URI` → `general_logs` | HU_S4_02; tolerante a fallos (cola + reintento) |
| Interacciones UI | MongoDB `MONGODB_INTERACTIONS_URI` → `interacciones` | HU_S4_03 (lotes desde frontend) |
| Logs de infraestructura | stdout → Fluent Bit → Loki | Operación diaria / errores de plataforma |
| Histórico | Object Storage (JSONL.gz) | Export bimestral (informe §3) |

## Variables de entorno

Ver `.env.example`:

- `MONGODB_GENERAL_URI` / `MONGODB_GENERAL_URI_DB`
- `MONGODB_INTERACTIONS_URI` / `MONGODB_INTERACTIONS_URI_DB`
- `MPDW_OBSERVABILITY_FAKE_MONGO=true` en CI/pruebas
- `REQUEST_LOGGING_ENABLED=true` para trazar HTTP en `general_logs`

## Grafana — fuentes y paneles (7 días)

1. Datasource **PostgreSQL** (MPDW) → consultas a `Auditoria`.
2. Datasource **MongoDB** (plugin o JSON API) → `general_logs` e `interacciones`.
3. Datasource **Loki** (cuando Fluent Bit esté desplegado) → logs stdout.
4. Importar `docs/observability/grafana-dashboards.json`.

### Acceso

Solo **Administrador** y **Analista de datos**. No publicar Loki ni Mongo al público; Grafana detrás de HTTPS y autenticación.

### Paneles sugeridos

- Login fallidos por hora (`LOGIN_FALLIDO`).
- Cambios de contraseña (`CAMBIO_PASSWORD`).
- Volumen `general_logs` por `accion` / `tipo`.
- Clics por `pantalla` y `boton` (interacciones); WhatsApp promo por `id_promocion`.
- Errores y p95 de latencia desde Loki (cuando aplique).

## Retención (punto de partida del informe)

| Almacén | Retención operativa | Histórico |
|---------|---------------------|-----------|
| Loki | 30–60 días | Export bimestral 12 meses en Object Storage |
| Mongo logs/interacciones | Ajustar al volumen (p. ej. 60–90 días) | Mismo ciclo de archivo si se requiere |
| PostgreSQL Auditoria | Permanente (seguridad de cuentas) | N/A |

## Despliegue de referencia (Compose)

Plantilla opcional: `docs/observability/docker-compose.observability.yml` (Fluent Bit + Loki + Grafana). Sustituir por el stack del proveedor si ya existe un servicio de logs administrado.

## Prueba de humo

1. Login fallido → fila en `Auditoria` + evento en Grafana.
2. Operación de negocio (p. ej. editar evento) → documento en `general_logs`, **no** en `Auditoria`.
3. Clic WhatsApp en promoción → lote en `interacciones`.
4. Apagar Mongo temporalmente → la API del usuario sigue respondiendo 2xx.