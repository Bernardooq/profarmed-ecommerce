# Profarmed — Motor de Sincronización ERP (sync_alpha)

Módulo de sincronización de bases de datos **Visual FoxPro (DBF)** e imágenes de catálogo hacia la API de **Profarmed** (`https://api.profarmed.com.mx/api/v1`).

---

## 📁 Estructura del Proyecto

```text
sync_alpha/
├── .gitignore
├── README.md
├── requirements.txt
├── docs/                           # Guías de servicio Windows y arquitectura cloud
├── logs/                           # Logs generados por los runners (.bat / .vbs)
├── runners/                        # Scripts .bat y .vbs para Task Scheduler
│   ├── upload_all_zip.bat|.vbs         # Sync completo GZIP (recomendado)
│   ├── upload_products_zip.bat|.vbs    # Catálogo y precios GZIP
│   ├── upload_users_zip.bat|.vbs       # Vendedores y clientes GZIP
│   ├── sync_all_batch.bat|.vbs         # Sync completo multithread por lotes
│   ├── sync_products_batch.bat|.vbs    # Catálogo y precios por lotes
│   ├── sync_users_batch.bat|.vbs       # Vendedores y clientes por lotes
│   ├── compress_images.bat|.vbs        # Compresión adaptativa a WebP
│   ├── aws_s3_sync_images.bat|.vbs     # Subida de WebP a S3 (profarmed-imgs)
│   ├── run_daily_images.bat            # Pipeline diario: comprimir + subir a S3
│   └── configure_aws.bat               # Configura perfil AWS (s3-sync-profarmed)
└── src/
    ├── config.py                   # Rutas DBF, credenciales API, filtros y lotes
    ├── extractors/                 # Lectores DBF (producto, existe, PRECIPROD, clientes, agentes)
    ├── transformers/               # Limpieza de datos y builders JSON
    ├── uploader/                   # Cliente API + scripts zip y batch
    └── images/                     # Compresor adaptativo WebP y analizador de tamaños
```

---

## 🚀 Ejecución Manual (desde `sync_alpha/`)

```powershell
# Instalación inicial
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Sincronización GZIP (Bulk Queue)
python -m src.uploader.sync_all_zip
python -m src.uploader.sync_products_zip
python -m src.uploader.sync_users_zip

# Sincronización Multithread por Lotes
python -m src.uploader.sync_all_batch
python -m src.uploader.sync_products_batch
python -m src.uploader.sync_users_batch

# Imágenes a WebP
python -m src.images.compress_images
python -m src.images.list_files_by_size
```
