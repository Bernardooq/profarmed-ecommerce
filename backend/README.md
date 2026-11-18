# Profarmed — Backend API & Microservicios

API RESTful de alto rendimiento desarrollada con **FastAPI** y **SQLAlchemy 2.0**, diseñada para soportar operaciones B2B concurrentes, catálogos extensos de medicamentos, consultas difusas (*fuzzy search* con `pg_trgm`), autenticación granular basada en roles (RBAC) y sincronización con almacén/ERP.

---

## 🏛️ Arquitectura del Backend

```
backend/
├── profarmed_api/              # Módulo raíz de la aplicación
│   ├── main.py                # Punto de entrada FastAPI, CORS, middleware y routers
│   ├── dependencies.py        # Inyección de dependencias (get_db, get_current_user, etc.)
│   ├── core/                  # Configuración global y seguridad criptográfica
│   │   ├── config.py          # Configuración Pydantic/BaseSettings y lectura de .env
│   │   └── security.py        # Hashing de passwords (Bcrypt/Passlib) y JWT tokens
│   ├── db/                    # Conexión y modelos de base de datos
│   │   ├── session.py         # Motor de base de datos con pool optimizado y SessionLocal
│   │   └── base.py            # Modelos declarativos SQLAlchemy (Tablas, Enums, ForeignKeys)
│   ├── routes/                # Controladores y endpoints REST modularizados
│   │   ├── auth.py            # Login regular, login sync, tokens JWT y logout
│   │   ├── products.py        # Catálogo, fuzzy search, subida y versionado de imágenes WebP
│   │   ├── categories.py      # Árbol de categorías y clasificación de medicamentos
│   │   ├── price_lists.py     # Listas de precios por cliente y cálculos de markups
│   │   ├── orders.py          # Ciclo de vida de pedidos, validación y asignación a vendedores
│   │   ├── cart.py            # Carrito persistente y validación de existencias
│   │   ├── client_request.py  # Solicitudes KYC "Quiero ser cliente" con documentos en S3
│   │   ├── announcement.py    # Banners de promociones (stories, popups, footers)
│   │   ├── tickets.py         # Sistema de tickets de soporte y mensajería
│   │   └── admin.py           # Dashboard administrativo y métricas
│   ├── schemas/               # Modelos de validación y serialización Pydantic v2
│   ├── crud/                  # Capa de acceso a datos y consultas de base de datos
│   └── utils/                 # Utilidades (cálculo de precios, similaridad, email SMTP)
├── create_initial_admins.py   # Siembra automatizada de administradores con retry logic
├── Dockerfile                 # Imagen Docker basada en python:3.11-slim
└── requirements.txt           # Dependencias fijadas para entornos reproducibles
```

---

## 🔑 Roles y Sistema de Permisos (RBAC)

La base de datos separa formalmente a los usuarios internos (`users`) de los clientes (`customers`):

| Rol | Alcance | Endpoints Típicos |
|---|---|---|
| **Admin** | Control total de la plataforma | Gestión de catálogo, asignación de grupos de venta, banners, KYC, usuarios |
| **Marketing** | Gestión comercial | Banners de anuncios, promociones, historias y campañas |
| **Seller** | Vendedor asignado a cartera | Aprobación/validación de pedidos, seguimiento a clientes asignados |
| **Customer** | Cliente farmacia / droguería | Consulta de catálogo con sus precios asignados, pedidos, favoritos, tickets |

---

## ⚙️ Configuración y Variables de Entorno

El backend requiere un archivo `.env` ubicado en `backend/profarmed_api/.env`:

```ini
# Base de Datos
DATABASE_URL=postgresql://usuario:password@localhost:5432/profarmed_db

# JWT
SECRET_KEY=tu_clave_secreta_jwt_muy_segura
ALGORITHM=HS256

# AWS S3 / CloudFront
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_REGION=us-east-1
BUCKET_DOCS=nombre-bucket-docs
BUCKET_PROMOS=nombre-bucket-promos
BUCKET_IMGS=nombre-bucket-imgs
CLOUDFRONT_PROMOS_URL=promos.dominio.com
CLOUDFRONT_IMGS_URL=img.dominio.com

# SMTP Email
SMTP_HOST=smtp.mailersend.net
SMTP_PORT=587
SMTP_USER=usuario_smtp
SMTP_PASSWORD=password_smtp
SENDER=notificaciones@dominio.com
```

---

## 🚀 Ejecución en Desarrollo

### Con Docker Compose (Recomendado)
Desde la raíz del repositorio:
```bash
docker compose up backend
```

### De Forma Nativa (Virtualenv)
```bash
cd backend
python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python create_initial_admins.py
uvicorn profarmed_api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📖 Documentación Interactiva de la API

Una vez iniciado el backend:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
