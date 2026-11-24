# SmartGarden API

Backend IoT para monitorear módulos de jardinería inteligente, plantas y lecturas
de sensores. Está construido con Django REST Framework, autenticación JWT y
aislamiento multiusuario.

---

## 📦 Entregables Oficiales — Evaluación Sumativa 4

| Entregable | Archivo / Recurso | Descripción |
| :--- | :--- | :--- |
| **Informe de Valor (Entregable 7)** | [`docs/INFORME_DE_VALOR_EVA4.md`](./docs/INFORME_DE_VALOR_EVA4.md) | Justificación de arquitectura, usuarios, problema y 3 características avanzadas (IA, Tiempo Real, 3D/Gráficos). |
| **Guion Video Demostrativo (Entregable 6)** | [`docs/GUION_VIDEO_DEMOSTRATIVO.md`](./docs/GUION_VIDEO_DEMOSTRATIVO.md) | Pauta cronológica minuto a minuto (6 a 10 min) con roles divididos entre Alexander Cortés y Angelo Zamora. |
| **Pruebas Automatizadas Postman** | [`tests/SmartGarden_EVA4_Postman_Collection.json`](./tests/SmartGarden_EVA4_Postman_Collection.json) | Colección v2.1 con aserciones para Auth JWT, FloraBot IA, CRUD Macetas y Catálogo (200 OK, 400, 401). |
| **Plantilla de Entorno Seguro** | [`.env.example`](./.env.example) | Variables de entorno del servidor (PostgreSQL, Groq Cloud, Django Secret). |
| **Documentación Swagger / OpenAPI** | [https://smart-garden-api-django.vercel.app/api/docs/](https://smart-garden-api-django.vercel.app/api/docs/) | Documentación interactiva de la API REST en producción. |
| **API en Producción (Vercel)** | [https://smart-garden-api-django.vercel.app/](https://smart-garden-api-django.vercel.app/) | Despliegue cloud del backend en producción. |
| **Portal Web Consumidor (Vercel)** | [https://smart-garden-web-react.vercel.app/](https://smart-garden-web-react.vercel.app/) | Cliente consumidor web con Gemelo 3D, Chart.js y FloraBot IA. |

---

## 🏗️ Diagrama Formal de Arquitectura Backend y Ecosistema

Diagrama formal de arquitectura de software estratificado con estereotipos normativos (UML Component & Deployment):

```mermaid
flowchart TD
    %% Estilos formales de alto contraste para Modo Oscuro y Modo Claro
    classDef actorStyle fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#ffffff;
    classDef clientStyle fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ffffff;
    classDef brokerStyle fill:#451a03,stroke:#fbbf24,stroke-width:2px,color:#ffffff;
    classDef backendStyle fill:#3b0764,stroke:#c084fc,stroke-width:2px,color:#ffffff;
    classDef dbStyle fill:#0f172a,stroke:#94a3b8,stroke-width:2px,color:#ffffff;
    classDef extStyle fill:#500724,stroke:#f472b6,stroke-width:2px,color:#ffffff;
    classDef hwStyle fill:#164e63,stroke:#22d3ee,stroke-width:2px,color:#ffffff;

    subgraph USUARIOS["👥 Capa de Usuarios"]
        Operador["«actor»<br/><b>Operador / Agricultor</b><br/>Monitoreo y Control Agronómico"]:::actorStyle
    end

    subgraph CLIENTES["📱 Capa de Clientes (Frontend)"]
        WebApp["«component»<br/><b>Portal Web (SPA)</b><br/>React 19 • Three.js • Chart.js<br/><b>★ Caract. 2: 3D &amp; Gráficos Dinámicos</b>"]:::clientStyle
        MobileApp["«component»<br/><b>Cliente Móvil Nativo</b><br/>Android • Kotlin • Jetpack Compose"]:::clientStyle
    end

    subgraph REALTIME["⚡ Capa de Tiempo Real (Baja Latencia)"]
        Firebase[("«database: NoSQL»<br/><b>Firebase Realtime Database</b><br/>Broker Pub/Sub Multi-Tenant<br/><b>★ Caract. 1: Tiempo Real &lt; 30ms</b>")]:::brokerStyle
    end

    subgraph BACKEND["⚙️ Capa de Negocio (Backend Serverless)"]
        DjangoAPI["«component»<br/><b>API REST Core</b><br/>Django 5.x • DRF • SimpleJWT<br/>Gestión de Macetas, Catálogo y Proxy IA"]:::backendStyle
    end

    subgraph SERVICIOS["💾 Persistencia &amp; Servicios Cloud"]
        SupabaseDB[("«database: RDBMS»<br/><b>PostgreSQL Transaccional</b><br/>Supabase Cloud (Pooler 5432)")]:::dbStyle
        GroqCloud["«external service»<br/><b>Inferencia IA (FloraBot)</b><br/>GroqCloud • openai/gpt-oss-120b<br/><b>★ Caract. 3: Procesamiento con IA</b>"]:::extStyle
    end

    subgraph IOT["🌱 Capa de Hardware / Ingesta IoT"]
        Sensores["«hardware: sensor»<br/>DHT11 &amp; LDR / Simulador"]:::hwStyle
        ESP32["«device»<br/><b>ESP32 DevKit / Simulator</b><br/>Firmware C/C++ / iot_simulator.py"]:::hwStyle
        Actuadores["«hardware: actuator»<br/>Relés Bomba &amp; Nebulizador"]:::hwStyle

        Sensores -->|"Lectura GPIO/ADC"| ESP32
        ESP32 -->|"Control Digital"| Actuadores
    end

    %% Flujos de interacción de Usuarios
    Operador -->|"Navegación HTTPS"| WebApp
    Operador -->|"Interacción Táctil"| MobileApp

    %% Flujos de Telemetría y Tiempo Real
    ESP32 ==>|"HTTP PUT (JSON / WiFi)"| Firebase
    Firebase ==>|"Streaming SSE (sub-30ms)"| MobileApp
    Firebase <==>|"EventSource Bidireccional"| WebApp

    %% Flujos de Autenticación y Negocio REST
    WebApp -->|"HTTPS / REST (JWT Bearer)"| DjangoAPI
    MobileApp -->|"HTTPS / REST (JWT Bearer)"| DjangoAPI

    %% Flujos de Persistencia y LLM
    DjangoAPI <-->|"SQL / TCP 5432"| SupabaseDB
    DjangoAPI <-->|"HTTPS / REST"| GroqCloud
```

---

## Características

- Gestión de módulos IoT asociados al usuario autenticado.
- Asociación de una planta por módulo, con umbrales personalizables.
- Ingesta y consulta histórica de telemetría.
- Filtros de telemetría por módulo y rango de fechas.
- Catálogo inicial de plantas comunes en Chile con imágenes y parámetros recomendados.
- Búsqueda de especies mediante un proxy seguro hacia la API botánica externa.
- **FloraBot IA**: Asistente agronómico inteligente con Groq LLM e inyección de telemetría en tiempo real.
- Documentación interactiva con OpenAPI y Swagger UI.
- Simulador de lecturas IoT incluido en `iot_simulator.py`.

## Requisitos

- Python 3.12 o superior.
- PostgreSQL o Supabase.
- Una API key de la API de plantas configurada en `PLANT_API_KEY`.
- Una API key de Groq configurada en `GROQ_API_KEY` para el asistente botánico FloraBot.

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
La ruta raíz (`/`) redirige al panel administrativo: Django muestra el inicio
de sesión si no hay una sesión activa y el panel si el usuario ya está
autenticado.

## Autenticación

Todos los endpoints de la API, excepto los recursos administrativos de Django,
requieren un token JWT. Obtener tokens:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ ^
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

El token de acceso dura 60 minutos y el de renovación dura 30 días.

## Endpoints principales

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/token/` | Obtener tokens JWT |
| POST | `/api/token/refresh/` | Renovar el token de acceso |
| POST | `/api/auth/register/` | Registrar usuario y obtener tokens JWT |
| GET/POST | `/api/modules/` | Listar o crear módulos propios |
| GET/PATCH/DELETE | `/api/modules/<id>/` | Consultar o modificar un módulo propio |
| POST | `/api/modules/<id>/telemetry/` | Registrar una lectura para un módulo |
| GET/POST | `/api/user-plants/` | Listar o asignar plantas |
| GET/PATCH/DELETE | `/api/user-plants/<id>/` | Gestionar una planta asignada |
| GET/POST | `/api/telemetry/` | Consultar o registrar telemetría |
| GET | `/api/plants/search/` | Catálogo inicial de especies botánicas |
| GET | `/api/plants/search/?q=monstera` | Buscar especies botánicas |
| POST | `/api/chat/` | Asistente agronómico inteligente FloraBot (Groq LLM) |
| GET | `/api/schema/` | Especificación OpenAPI |
| GET | `/api/docs/` | Swagger UI |
| GET | `/admin/` | Panel administrativo de Django |

Cada usuario solo puede acceder a sus propios módulos, plantas y registros de
telemetría.

Las rutas `/api/auth/login/` y `/api/auth/refresh/` se mantienen como alias
compatibles para clientes existentes. Los nuevos clientes deben usar
`/api/token/` y `/api/token/refresh/`.

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

Consultar al asistente botánico FloraBot (IA):

```bash
curl -X POST http://127.0.0.1:8000/api/chat/ ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"¿Cómo está mi planta?\",\"plant_context\":{\"name\":\"Monstera Deliciosa\",\"temperature\":24.5,\"soil_moisture\":52,\"light_lux\":78}}"
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
   DJANGO_ALLOWED_HOSTS=smart-garden-api-django.vercel.app
   DATABASE_URL=postgresql://...
   PLANT_API_BASE_URL=https://perenual.com/api/species-list
   PLANT_API_KEY=<api-key>
   CORS_ALLOWED_ORIGINS=https://smart-garden-web-react.vercel.app
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
https://smart-garden-api-django.vercel.app/api/docs/
https://smart-garden-api-django.vercel.app/admin/
```

URLs públicas:

```text
Backend:  https://smart-garden-api-django.vercel.app/
Frontend: https://smart-garden-web-react.vercel.app/
```

La aplicación web y Android deben usar la URL pública del backend incluyendo
`/api`:
`https://smart-garden-api-django.vercel.app/api`.
