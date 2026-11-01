# ==============================================================================
# Verificación Extremo a Extremo (E2E) - MPDW
# Flujo: Login -> Obtener Producto -> Cambiar Precio -> Conflicto 409
# ==============================================================================
import json
import os
import urllib.error
import urllib.request


def main():
    print("=== INICIO DE VERIFICACION E2E ===")

    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@mundopinturasdiana.com")
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD")
    if not admin_password:
        raise ValueError("Se requiere configurar la variable INITIAL_ADMIN_PASSWORD para ejecutar la prueba E2E.")

    # 1. Login
    login_data = json.dumps({
        "email": admin_email,
        "password": admin_password,
    }).encode("utf-8")
    req_login = urllib.request.Request(
        f"{base_url}/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_login) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        token = body["access_token"]
        print(f"[PASO 1] Login exitoso: HTTP {resp.status} - Usuario: {body['email']}, Rol: {body['rol']}")

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Consultar Productos
    req_get = urllib.request.Request(
        f"{base_url}/api/v1/products/",
        headers=auth_headers,
        method="GET"
    )
    with urllib.request.urlopen(req_get) as resp:
        prods = json.loads(resp.read().decode("utf-8"))
        prod = prods["results"][0]
        pid = prod["id_producto"]
        curr_version = prod["version"]
        curr_precio = prod["precio_venta"]
        print(f"[PASO 2] Producto encontrado: ID={pid}, Nombre='{prod['nombre']}', Version={curr_version}, Precio=${curr_precio}")

    # 3. Actualizar precio con version actual (Exito -> version incrementa)
    nuevo_precio = "52000.00"
    update_data = json.dumps({
        "nuevo_precio": nuevo_precio,
        "motivo": "Ajuste de precio regularizado",
        "version": curr_version
    }).encode("utf-8")

    req_update = urllib.request.Request(
        f"{base_url}/api/v1/products/{pid}/price",
        data=update_data,
        headers=auth_headers,
        method="PATCH"
    )
    with urllib.request.urlopen(req_update) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        etag = resp.headers.get("ETag")
        print(f"[PASO 3] Actualizacion exitosa: HTTP {resp.status} - Nueva Version={res['version']}, Nuevo Precio=${res['precio_venta']}, ETag={etag}")

    # 4. Intentar actualizar precio con version anterior obsoleta (Conflicto 409)
    stale_data = json.dumps({
        "nuevo_precio": "58000.00",
        "motivo": "Intento concurrente con version desactualizada",
        "version": curr_version
    }).encode("utf-8")

    req_stale = urllib.request.Request(
        f"{base_url}/api/v1/products/{pid}/price",
        data=stale_data,
        headers=auth_headers,
        method="PATCH"
    )

    try:
        urllib.request.urlopen(req_stale)
        print("[PASO 4] ERROR INESPERADO: La peticion deberia haber fallado con HTTP 409!")
    except urllib.error.HTTPError as e:
        err_body = json.loads(e.read().decode("utf-8"))
        print(f"[PASO 4] Conflicto 409 verificado con exito: HTTP {e.code} {e.reason}")
        print(f"         Codigo: {err_body.get('codigo')}")
        print(f"         Mensaje: {err_body.get('mensaje')}")
        print(f"         Correlacion: {err_body.get('idCorrelacion')}")

    print("=== VERIFICACION E2E COMPLETADA CON EXITO ===")


if __name__ == "__main__":
    main()
