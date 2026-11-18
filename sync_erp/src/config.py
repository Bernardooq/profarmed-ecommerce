"""
Configuración centralizada para el sincronizador ERP de Profarmed.
Carga variables de entorno desde .env si existe o utiliza valores seguros por defecto.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz de sync_erp o desde src/
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

# ============================================================================
# BACKEND API CONFIGURATION
# ============================================================================

BACKEND_URL = os.getenv("BACKEND_URL", "https://apiecommerce.profarmed.com.mx/api/v1")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "syncadminssuser2026")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "SyncProfarmed2026!Key")

# ============================================================================
# ERP SQL DATABASE CONFIGURATION
# ============================================================================

ERP_DB_DRIVER = os.getenv("ERP_DB_DRIVER", "SQL Server")
ERP_DB_HOST = os.getenv("ERP_DB_HOST", "127.0.0.1")
ERP_DB_PORT = int(os.getenv("ERP_DB_PORT", "1433"))
ERP_DB_NAME = os.getenv("ERP_DB_NAME", "erp_profarmed")
ERP_DB_USER = os.getenv("ERP_DB_USER", "sa")
ERP_DB_PASSWORD = os.getenv("ERP_DB_PASSWORD", "")

# ============================================================================
# IMAGES & CDN CONFIGURATION
# ============================================================================

CDN_URL = os.getenv("CDN_URL", "https://imgecommerce.profarmed.com.mx")
S3_BUCKET = os.getenv("S3_BUCKET", "profarmed-imgs")

IMAGES_FOLDER_INPUT = Path(os.getenv("IMAGES_FOLDER_INPUT", r"C:\Users\berna\Downloads\Imagenes"))
IMAGES_FOLDER_OUTPUT = Path(os.getenv("IMAGES_FOLDER_OUTPUT", r"C:\Users\berna\Downloads\CompressedImg"))
IMAGES_FOLDER = Path(os.getenv("IMAGES_FOLDER") or str(IMAGES_FOLDER_OUTPUT))

# ============================================================================
# FILTROS Y REGLAS DE NEGOCIO
# ============================================================================

PRODUCTOS_BLOQUEADOS = {'99999', '99998', '100', '99'}
CATEGORIA_BLOQUEADA = 'GASTOS'

# Tamaño de lotes si se procesan en memoria
BATCH_SIZE = {
    "categorias": 100,
    "productos": 500,
    "listas": 100,
    "items": 2000,
    "users": 200
}

