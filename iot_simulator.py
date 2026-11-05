import os
import sys
import time
import random
import requests

# ==========================================================
# CONFIGURACIÓN DEL SIMULADOR IoT (SmartGarden)
# ==========================================================
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api")

# Reemplaza con las credenciales de tu superusuario
USERNAME = os.environ.get("IOT_USER", "admin")
PASSWORD = os.environ.get("IOT_PASS", "1QAZxsw2!")

# ID del módulo objetivo (por defecto el módulo 1)
TARGET_MODULE_ID = int(os.environ.get("IOT_MODULE_ID", 1))
INTERVAL_SECONDS = 5


def get_jwt_token(username: str, password: str) -> str:
    """
    1. Autentica contra /api/auth/login/ y retorna el token JWT de acceso.
    """
    login_url = f"{API_BASE_URL}/auth/login/"
    print(f"[*] Autenticando usuario '{username}' en {login_url} ...")

    try:
        response = requests.post(
            login_url,
            json={"username": username, "password": password},
            timeout=10,
        )
        response.raise_for_status()
        tokens = response.json()
        access_token = tokens.get("access")
        if not access_token:
            raise ValueError("La respuesta no contiene un token 'access'.")
        print("[+] Token JWT obtenido exitosamente.")
        return access_token
    except requests.exceptions.RequestException as exc:
        print(f"[!] Error al autenticar: {exc}")
        if getattr(exc, "response", None) is not None:
            print(f"    Detalle del servidor: {exc.response.text}")
        sys.exit(1)


def get_module_id(access_token: str, preferred_id: int = 1) -> int:
    """
    2. Consulta /api/modules/ con el Bearer Token para verificar/obtener el ID del módulo.
    Prioriza el módulo indicado (por defecto ID = 1) o toma el primero disponible.
    """
    modules_url = f"{API_BASE_URL}/modules/"
    headers = {"Authorization": f"Bearer {access_token}"}

    print(f"[*] Consultando módulos disponibles en {modules_url} ...")
    try:
        response = requests.get(modules_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Soporta tanto respuesta paginada (PageNumberPagination) como lista directa
        modules = data.get("results", data) if isinstance(data, dict) else data

        if not modules:
            print(
                f"[!] No se encontraron módulos en la cuenta, se usará el ID configurado ({preferred_id})."
            )
            return preferred_id

        # Buscar si existe el módulo con preferred_id (1); si no, usar el primero de la lista
        for mod in modules:
            if mod.get("id") == preferred_id:
                print(
                    f"[+] Módulo seleccionado: ID={mod['id']} | Nombre='{mod.get('nombre')}' | MAC={mod.get('mac_address')}"
                )
                return mod["id"]

        first_mod = modules[0]
        print(
            f"[+] Módulo {preferred_id} no encontrado; usando el primer módulo: ID={first_mod['id']} ({first_mod.get('nombre')})"
        )
        return first_mod["id"]

    except requests.exceptions.RequestException as exc:
        print(f"[!] Error al obtener módulos: {exc}")
        if getattr(exc, "response", None) is not None:
            print(f"    Detalle del servidor: {exc.response.text}")
        sys.exit(1)


def generate_sensor_payload() -> dict:
    """
    3. Genera lecturas aleatorias realistas dentro de los rangos especificados.
    """
    return {
        "temperatura": round(random.uniform(20.0, 35.0), 2),
        "humedad": round(random.uniform(30.0, 80.0), 2),
        "luz": round(random.uniform(400.0, 1000.0), 2),
    }


def run_simulator():
    """
    4. Ejecuta el ciclo infinito de envío de telemetría cada 5 segundos.
    """
    access_token = get_jwt_token(USERNAME, PASSWORD)
    module_id = get_module_id(access_token, preferred_id=TARGET_MODULE_ID)

    ingest_url = f"{API_BASE_URL}/modules/{module_id}/telemetry/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    print(f"\n[*] Iniciando transmisión IoT hacia {ingest_url} (cada {INTERVAL_SECONDS}s).")
    print("[*] Presiona Ctrl+C para detener el simulador.\n")

    try:
        while True:
            payload = generate_sensor_payload()
            try:
                response = requests.post(
                    ingest_url,
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                if response.status_code == 201:
                    data = response.json()
                    print(
                        f"[OK 201] ({data.get('timestamp', 'now')}) -> "
                        f"Temp: {payload['temperatura']}°C | "
                        f"Hum: {payload['humedad']}% | "
                        f"Luz: {payload['luz']} lx"
                    )
                else:
                    print(
                        f"[ERROR {response.status_code}] Respuesta: {response.text}"
                    )
            except requests.exceptions.RequestException as exc:
                print(f"[!] Error de red enviando telemetría: {exc}")

            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n[*] Simulador IoT detenido por el usuario.")


if __name__ == "__main__":
    run_simulator()

