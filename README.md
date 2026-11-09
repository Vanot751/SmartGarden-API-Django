# SmartGarden API

Backend IoT para monitorear módulos de jardinería inteligente, plantas y lecturas
de sensores. Está construido con Django REST Framework, autenticación JWT y
aislamiento multiusuario.

## Características

- Gestión de módulos IoT asociados al usuario autenticado.
- Asociación de una planta por módulo, con umbrales personalizables.
- Ingesta y consulta histórica de telemetría.
- Filtros de telemetría por módulo y rango de fechas.
- Catálogo inicial de plantas comunes en Chile con imágenes y parámetros recomendados.
- Búsqueda de especies mediante un proxy seguro hacia la API botánica externa.
- Documentación interactiva con OpenAPI y Swagger UI.
- Simulador de lecturas IoT incluido en `iot_simulator.py`.

## Requisitos

- Python 3.12 o superior.
- PostgreSQL o Supabase.
- Una API key de la API de plantas configurada en `PLANT_API_KEY`.

## Instalación

Desde la raíz del proyecto:

```bash
python -m venv .venv
```

Activar el entorno virtual:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear un archivo `.env` en la raíz:

```env
DJANGO_SECRET_KEY=cambia-esta-clave-en-produccion
DJANGO_DEBUG=True
DATABASE_URL=postgresql://usuario:contraseña@host:5432/smartgarden
PLANT_API_BASE_URL=https://perenual.com/api/species-list
PLANT_API_KEY=tu-api-key
```

Aplicar migraciones y crear un usuario administrador:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Iniciar el servidor:

```bash
python manage.py runserver
```

La API estará disponible en `http://127.0.0.1:8000`.

## Autenticación

Todos los endpoints de la API, excepto los recursos administrativos de Django,
requieren un token JWT. Obtener tokens:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"tu-contraseña\"}"
```

Respuesta:

```json
{
  "refresh": "token-de-refresh",
  "access": "token-de-acceso"
}
```

Usar el token de acceso en las peticiones protegidas:

```text
Authorization: Bearer <access-token>
```

El token de acceso dura 60 minutos y el de renovación dura 7 días.

## Endpoints principales

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/auth/login/` | Obtener tokens JWT |
| POST | `/api/auth/refresh/` | Renovar el token de acceso |
| GET/POST | `/api/modules/` | Listar o crear módulos propios |
| GET/PATCH/DELETE | `/api/modules/<id>/` | Consultar o modificar un módulo propio |
| POST | `/api/modules/<id>/telemetry/` | Registrar una lectura para un módulo |
| GET/POST | `/api/user-plants/` | Listar o asignar plantas |
| GET/PATCH/DELETE | `/api/user-plants/<id>/` | Gestionar una planta asignada |
| GET/POST | `/api/telemetry/` | Consultar o registrar telemetría |
| GET | `/api/plants/search/` | Catálogo inicial de especies botánicas |
| GET | `/api/plants/search/?q=monstera` | Buscar especies botánicas |
| GET | `/api/schema/` | Especificación OpenAPI |
| GET | `/api/docs/` | Swagger UI |
| GET | `/admin/` | Panel administrativo de Django |

Cada usuario solo puede acceder a sus propios módulos, plantas y registros de
telemetría.

## Ejemplos de uso

Crear un módulo:

```bash
curl -X POST http://127.0.0.1:8000/api/modules/ ^
  -H "Authorization: Bearer <access-token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"mac_address\":\"AA:BB:CC:DD:EE:FF\",\"nombre\":\"Maceta sala\"}"
```

Asignar una planta a un módulo:

```json
{
  "module": 1,
  "api_species_id": "123",
  "apodo": "Monstera",
  "temp_min": 15,
  "temp_max": 30,
  "humedad_optima": 60
}
```

Registrar telemetría:

```bash
curl -X POST http://127.0.0.1:8000/api/modules/1/telemetry/ ^
  -H "Authorization: Bearer <access-token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"temperatura\":24.5,\"humedad\":62.0,\"luz\":750.0}"
```

Filtrar telemetría:

```text
GET /api/telemetry/?module=1&start_date=2026-11-01T00:00:00Z&end_date=2026-11-05T23:59:59Z
```

Los resultados se entregan paginados, con un máximo de 50 registros por página.

## Simulador IoT

Con el servidor ejecutándose y al menos un módulo creado, configurar
opcionalmente las variables del simulador:

```powershell
$env:API_BASE_URL="http://127.0.0.1:8000/api"
$env:IOT_USER="admin"
$env:IOT_PASS="tu-contraseña"
$env:IOT_MODULE_ID="1"
python iot_simulator.py
```

El simulador obtiene un JWT, selecciona el módulo indicado y envía lecturas
aleatorias cada 5 segundos. Detenerlo con `Ctrl+C`.

## Desarrollo y pruebas

Comprobar la configuración de Django:

```bash
python manage.py check
```

Ejecutar las pruebas:

```bash
python manage.py test
```

## Producción

- Usar una `DJANGO_SECRET_KEY` segura y mantener `DJANGO_DEBUG=False`.
- No incluir `.env` ni API keys en el repositorio.
- Configurar correctamente `DATABASE_URL` y las credenciales de la API externa.
- Restringir `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` a los dominios reales.
- Ejecutar detrás de un servidor WSGI/ASGI y HTTPS.

## Despliegue en Vercel

Este repositorio es detectado automáticamente como una aplicación Django porque
contiene `manage.py`. Vercel usa `config/wsgi.py` como una Function y ejecuta
`collectstatic` automáticamente porque `STATIC_ROOT` está configurado.

### Configuración del proyecto

1. En Vercel, seleccionar **Add New Project > Import Git Repository** y elegir
   este repositorio.
2. Dejar el **Root Directory** en la raíz del repositorio.
3. No configurar un Build Command personalizado. Vercel instala
   `requirements.txt` y detecta Django automáticamente.
4. Configurar estas variables en **Settings > Environment Variables**:

   ```text
   DJANGO_SECRET_KEY=<clave-secreta-larga-y-aleatoria>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=<proyecto>.vercel.app
   DATABASE_URL=postgresql://...
   PLANT_API_BASE_URL=https://perenual.com/api/species-list
   PLANT_API_KEY=<api-key>
   CORS_ALLOWED_ORIGINS=https://<frontend>.vercel.app
   ```

   `DATABASE_URL` debe apuntar a PostgreSQL/Supabase. No se debe usar una base
   SQLite local en Vercel porque el sistema de archivos de las Functions no es
   persistente.
5. Hacer clic en **Deploy**. Cada push a la rama de producción crea un nuevo
   despliegue; los pull requests pueden crear despliegues de preview.

### Migraciones y superusuario

Las migraciones deben ejecutarse contra la base de datos de producción, no
durante cada invocación de la Function:

```bash
vercel env pull .env.local
python manage.py migrate
python manage.py createsuperuser
```

También se pueden ejecutar desde una máquina con acceso a la misma
`DATABASE_URL`, manteniendo `.env.local` fuera del repositorio.

Después del despliegue, comprobar:

```text
https://<proyecto>.vercel.app/api/docs/
https://<proyecto>.vercel.app/admin/
```

La aplicación Android debe usar la URL pública incluyendo `/api`, por ejemplo:
`https://<proyecto>.vercel.app/api`.
