# Profarmed — Motor de Sincronización ERP (SQL Sync Engine)

Módulo cliente especializado en la extracción directa desde bases de datos **SQL ERP (Alpha / ERP)**, normalización y empaquetado en lotes comprimidos en **GZIP** hacia la API de **Profarmed**.

---

## 🏛️ Estructura del Proyecto

```text
sync_erp/
├── README.md                   # Esta guía técnica
├── requirements.txt            # Dependencias del cliente (requests, pandas, etc.)
├── .env.example                # Plantilla de variables de entorno
├── .gitignore                  # Exclusión de venvs, logs y cachés
│
├── runners/                    # Scripts de ejecución (.bat y .vbs) para Task Scheduler
│   ├── upload_products.bat     # Extracción y carga de catálogo y precios
│   ├── upload_products.vbs     # Lanzador silencioso en segundo plano
│   ├── upload_users.bat        # Extracción y carga de clientes y agentes
│   ├── upload_users.vbs        # Lanzador silencioso en segundo plano
│   ├── pull_orders.bat         # Descarga pedidos pendientes (is_synced=false) -> dbo.cotiza3
│   ├── pull_orders.vbs         # Lanzador silencioso en segundo plano
│   ├── upload_all.bat          # Sincronización consolidada (catálogo + usuarios)
│   ├── upload_all.vbs
│   ├── compress_images.bat     # Optimización de imágenes a WebP (<50KB)
│   ├── compress_images.vbs
│   └── aws_s3_sync_images.bat  # Sincronización a bucket S3 profarmed-imgs
│
├── src/                        # Código fuente modular en Python
│   ├── config.py               # Configuración centralizada (URLs, credenciales, DB)
│   │
│   ├── database/               # Capa de conexión y pools a la BD SQL del ERP
│   │   ├── __init__.py
│   │   └── connection.py       # Soporta pyodbc, pymssql, postgresql, etc.
│   │
│   ├── extractors/             # Consultas SQL para extraer entidades
│   │   ├── __init__.py
│   │   ├── products_extractor.py   # Consulta productos, descripciones, stock
│   │   ├── prices_extractor.py     # Consulta listas y renglones de precios
│   │   └── users_extractor.py      # Consulta agentes y clientes
│   │
│   ├── transformers/           # Limpieza, normalización y mapeo de datos
│   │   ├── __init__.py
│   │   ├── data_cleaning.py    # Funciones puras de limpieza (teléfonos, ladas, usernames)
│   │   └── builders.py         # Mapeo a esquemas JSON exactos de la API
│   │
│   ├── uploader/               # Pipelines de compresión GZIP y POST a la API
│   │   ├── __init__.py
│   │   ├── api_client.py       # Auth JWT (/auth/login/sync) y upload_compressed_json
│   │   ├── sync_products.py    # Runner de Catálogo y Precios
│   │   ├── sync_users.py       # Runner de Usuarios
│   │   ├── sync_orders.py      # Runner Pull & Upsert de Pedidos -> dbo.cotiza3
│   │   └── sync_all.py         # Runner consolidado
│   │
│   └── images/                 # Optimización de imágenes
│       ├── __init__.py
│       ├── compress_images.py
│       └── list_files_by_size.py
│
└── logs/                       # Bitácoras de ejecución generadas automáticamente
    └── .gitkeep
```

---

## ⚙️ Configuración (`.env`)

Crea un archivo `.env` en la raíz de `sync_erp/` basándote en `.env.example`:

```env
# Backend API Profarmed
BACKEND_URL=https://apiecommerce.profarmed.com.mx/api/v1
ADMIN_USERNAME=syncadminssuser2026
ADMIN_PASSWORD=SyncProfarmed2026!Key

# CDN CloudFront y Carpeta de Imágenes
CDN_URL=https://imgecommerce.profarmed.com.mx
S3_BUCKET=profarmed-imgs
IMAGES_FOLDER_INPUT=C:\Users\berna\Downloads\Imagenes
IMAGES_FOLDER_OUTPUT=C:\Users\berna\Downloads\CompressedImg

# Base de Datos SQL ERP
ERP_DB_DRIVER=SQL Server
ERP_DB_HOST=127.0.0.1
ERP_DB_PORT=1433
ERP_DB_NAME=erp_profarmed
ERP_DB_USER=sa
ERP_DB_PASSWORD=tu_password_aqui
```

---

## 🚀 Ejecución

### Desde Terminal / Línea de Comandos:

```bash
# Activar entorno virtual
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Sincronizar catálogo y precios
python src/uploader/sync_products.py

# Sincronizar usuarios (clientes y agentes)
python src/uploader/sync_users.py

# Descargar pedidos pendientes y realizar upsert en dbo.cotiza3
python src/uploader/sync_orders.py

# Sincronización completa consolidada
python src/uploader/sync_all.py
```

### Automatización en Windows (Programador de Tareas):

Para que los procesos corran periódicamente de forma invisible sin abrir ventanas de CMD:
1. Crear una tarea en el **Programador de Tareas de Windows**.
2. Acción: **Iniciar un programa**.
3. Programa o script: `wscript.exe`
4. Argumentos: `"C:\...\sync_erp\runners\upload_all.vbs"`
5. Iniciar en: `"C:\...\sync_erp\runners\"`

---

## 🖼️ Convención de Imágenes por Subcarpeta de Código de Barras

A diferencia del esquema tradicional plano (`<product_id>.webp`), en Profarmed las imágenes se organizan en subcarpetas por **código de barras** (`CODBAR` / `codebar`):

```text
Imagenes/                   (IMAGES_FOLDER_INPUT)
└── 1234323252/
    ├── 1.jpg
    └── 2.jpg

CompressedImg/              (IMAGES_FOLDER_OUTPUT -> s3://profarmed-imgs)
└── 1234323252/
    ├── 1.webp
    └── 2.webp
```

1. `compress_images.py` recorre recursivamente todas las subcarpetas de `IMAGES_FOLDER_INPUT` y guarda el resultado `.webp` conservando la ruta `<codigo_barras>/<archivo>.webp`.
2. `aws_s3_sync_images.bat` sube recursivamente todas las subcarpetas y archivos a S3 (`s3://%S3_BUCKET%`).
3. Durante el upsert de productos (`sync_products.py` / `sync_all.py`), `image_url` se resuelve así:
   - Si existe `<codigo_barras>/1.webp` -> `https://imgecommerce.profarmed.com.mx/<codigo_barras>/1.webp`.
   - Si no existe `1.webp` -> toma el primer archivo de imagen válido dentro de `<codigo_barras>/`.
   - Si la subcarpeta no existe o está vacía -> envía `image_url: null` (vacía).
