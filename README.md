# 🚀 Gigly — Marketplace de Servicios Freelance de Próxima Generación

**Gigly** es una plataforma web moderna para la contratación y venta de servicios profesionales y freelance, diseñada con una arquitectura de alto rendimiento en **Python (FastAPI)**, frontend estilizado con **Tailwind CSS** y **Alpine.js**, y persistencia relacional con **SQLAlchemy** (compatible con SQLite en desarrollo y PostgreSQL en Render).

A diferencia del modelo tradicional de plataformas como Fiverr, Gigly introduce **ventajas competitivas avanzadas**:
- 🛡️ **Gigly Escrow:** Retención de fondos en custodia bancaria segura hasta la aprobación del cliente.
- 💰 **Comisión Justa al Freelancer (10%):** La mitad de la comisión abusiva del 20% habitual en el sector.
- 🎯 **Pagos por Hitos (Milestones):** División de proyectos en fases con entregas y liberaciones parciales de fondos.
- 🔒 **Bóveda de Archivos con Marca de Agua Automática:** Protección visual procesada con Pillow para evitar el robo de entregables antes de liberar el pago.
- 📝 **Contratos NDA con 1 Clic:** Acuerdos de confidencialidad digitales con firma, timestamp y hash SHA-256.
- ⚡ **Tablero de Solicitudes Inversas (Subasta de Proyectos):** Los clientes publican necesidades con presupuesto abierto y los freelancers compiten con propuestas.
- 💬 **Chat en Tiempo Real & Videollamadas HD Integradas:** Mensajería WebSocket por pedido y salas seguras instantáneas de **Jitsi Meet**.
- 📊 **Panel de Analíticas Financieras:** Gráficos interactivos con **Chart.js** para seguimiento de ingresos netos, comisiones y proyecciones.

---

## 🏗️ 1. Estructura del Proyecto

```
D:\Proyectos\python\gigly\
├── app/
│   ├── __init__.py
│   ├── config.py              # Variables de entorno y rutas seguras
│   ├── database.py            # Engine, sessionmaker y soporte PostgreSQL/SQLite
│   ├── models.py              # Modelos ORM de SQLAlchemy (12 tablas)
│   ├── schemas.py             # Esquemas Pydantic para validación y tipos
│   ├── auth.py                # Hash de contraseñas Bcrypt y tokens JWT
│   ├── templating.py          # Renderizador de plantillas Jinja2 adaptado
│   ├── services/
│   │   ├── __init__.py
│   │   ├── escrow.py          # Lógica de custodia, comisiones y transacciones
│   │   ├── watermark.py       # Procesamiento de imágenes con marca de agua (Pillow)
│   │   └── jitsi.py           # Generador de salas y enlaces para Jitsi Meet
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth_routes.py     # Registro, login, logout y cambio dinámico de rol
│   │   ├── gigs_routes.py     # Catálogo, filtros y publicación de servicios
│   │   ├── orders_routes.py   # Checkout, Escrow, entregables, hitos, NDA y reviews
│   │   ├── requests_routes.py # Tablero de subastas y propuestas
│   │   ├── chat_routes.py     # WebSockets y API de mensajes
│   │   ├── wallet_routes.py   # Billetera, depósitos y retiros
│   │   └── analytics_routes.py# Analíticas para vendedores y Chart.js
│   ├── templates/             # Vistas Jinja2 con Tailwind CSS y Alpine.js
│   │   ├── base.html          # Layout principal (navbar, role switcher, footer)
│   │   ├── index.html         # Página de inicio con hero, categorías y gigs
│   │   ├── auth/              # login.html, register.html
│   │   ├── gigs/              # list.html, detail.html (3 tiers), create.html
│   │   ├── orders/            # checkout.html, detail.html (sala de pedido), list.html
│   │   ├── requests/          # list.html, detail.html, create.html
│   │   └── dashboard/         # wallet.html, analytics.html
│   └── static/
│       ├── css/custom.css     # Estilos y tema oscuro de Gigly
│       └── js/main.js         # Utilidades globales (switchRole, toasts)
├── uploads/                   # Directorio de subidas (gigs, entregables, watermarked)
├── main.py                    # Punto de entrada de la aplicación FastAPI
├── requirements.txt           # Dependencias completas del backend
├── Procfile                   # Comando de inicio para Render / Heroku
├── render.yaml                # Especificación para Render Blueprints
├── seed_data.py               # Script para poblar la BD con datos realistas
├── test_routes.py             # Suite de pruebas unitarias y funcionales
└── README.md                  # Documentación completa
```

---

## 🎨 2. Identidad Visual y Paleta de Colores

- **Fondo principal:** `#121417` (Negro carbón profundo)
- **Tarjetas y contenedores:** `#1A1D24`
- **Bordes sutiles:** `#262B35` / `#343B48`
- **Textos principales:** `#EAECEF`
- **Textos secundarios:** `#B0B5BD`
- **Color de acento:** Turquesa vibrante `#14B8A6` (Hover: `#0D9488`)
- **Tipografía:** *Plus Jakarta Sans* & *Inter* de Google Fonts.

---

## 💻 3. Instalación y Ejecución en Local

### Paso 1: Clonar o ingresar al directorio del proyecto
```bash
cd D:\Proyectos\python\gigly
```

### Paso 2: Crear y activar el entorno virtual
En Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Poblar la base de datos con datos de demostración
```bash
python seed_data.py
```
*Este comando crea las tablas y siembra usuarios de prueba, servicios con paquetes en 3 niveles, pedidos en curso, archivos en la bóveda protegida y contratos NDA.*

### Paso 5: Iniciar el servidor de desarrollo
```bash
uvicorn main:app --reload --port 8000
```
Abre tu navegador en: **`http://localhost:8000`**

---

## 🔑 4. Cuentas de Prueba Preconfiguradas

| Rol | Usuario | Correo Electrónico | Contraseña | Saldo Billetera |
| :--- | :--- | :--- | :--- | :--- |
| **SuperAdmin (Gigly)** | `admin_gigly` | `admin@gigly.com` | `admin123` | Control Global & Arbitraje |
| **Freelancer (Vendedor)** | `demo_freelancer` | `freelancer@gigly.com` | `password123` | $1,240.00 USD |
| **Cliente (Comprador)** | `demo_client` | `client@gigly.com` | `password123` | $850.00 USD |
| **Diseñadora UI/UX** | `sofia_ux` | `sofia@gigly.com` | `password123` | $620.00 USD |

> **Nota:** Puedes alternar instantáneamente entre el modo Comprador y Vendedor desde el botón ubicado en la barra de navegación superior.

---

## 🧪 5. Ejecutar la Suite de Pruebas
Para verificar el 100% de operatividad del sistema, ejecuta:
```bash
python test_routes.py
```

---

## 🚀 6. Despliegue en Render (Paso a Paso)

Gigly está preparado para migrar automáticamente de SQLite a PostgreSQL en Render:

1. **Crear repositorio en GitHub:**
   Sube el código a tu repositorio de GitHub:
   ```bash
   git init
   git add .
   git commit -m "Gigly Marketplace Initial Release"
   git branch -M main
   git remote add origin https://github.com/tu-usuario/gigly.git
   git push -u origin main
   ```

2. **Crear la Base de Datos PostgreSQL en Render:**
   - Ve a [render.com](https://render.com) y crea una nueva **PostgreSQL Database**.
   - Nombre: `gigly-db`.
   - Copia la **Internal Database URL** que Render te proporciona.

3. **Crear el Web Service en Render:**
   - Elige **New Web Service** conectado a tu repositorio de GitHub.
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Configurar Variables de Entorno en Render:**
   En la pestaña *Environment* del Web Service, añade:
   - `DATABASE_URL`: La URL de conexión de PostgreSQL proporcionada por Render (si inicia con `postgres://`, Gigly la normaliza automáticamente a `postgresql://`).
   - `SECRET_KEY`: Una clave secreta segura aleatoria.
   - `APP_ENV`: `production`
   - `PLATFORM_SELLER_FEE_PERCENT`: `10.0`
   - `PLATFORM_BUYER_FEE_PERCENT`: `3.0`

5. **Poblar la base de datos de producción (Opcional):**
   Desde la consola de Render (Shell tab):
   ```bash
   python seed_data.py
   ```

¡Tu marketplace Gigly estará en vivo y completamente funcional!
