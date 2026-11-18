"""
Configuración centralizada para scripts de sincronización DBF (Profarmed - sync_alpha).

Define rutas, credenciales API y filtros comunes utilizados por todos los
módulos de sincronización (zip, batch e imágenes).
"""

from pathlib import Path

# ============================================================================
# BACKEND API CONFIGURATION
# ============================================================================

BACKEND_URL = "https://api.profarmed.com.mx/api/v1"
# BACKEND_URL = "http://localhost:8000/api/v1"
ADMIN_USERNAME = "syncadminssuser2026"
ADMIN_PASSWORD = "SyncProfarmed2026!Key"

# ============================================================================
# FILE PATHS
# ============================================================================

# Directorio donde están los archivos DBF
BASE_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DBF_DIR = BASE_PROJECT_DIR / "backend" / "dbfs"
if not DBF_DIR.exists():
    DBF_DIR = Path(r"C:\Users\berna\Documents\GitProjects\profarmed-ecommerce\backend\dbfs")

# Directorio destino (WebP comprimidas) y origen (imágenes originales)
IMAGES_FOLDER = Path(r"C:\ecommerce\compressedIMG")
IMAGES_FOLDER_INPUT = Path(r"C:\VSAI\Empresas\PFC2026")

# URL del CDN para imágenes
CDN_URL = "https://img.profarmed.com.mx"

# ============================================================================
# DBF FILES
# ============================================================================

CLIENTES_DBF = DBF_DIR / "clientes.dbf"
AGENTES_DBF = DBF_DIR / "agentes.dbf"
PRODUCTO_DBF = DBF_DIR / "producto.dbf"
PRO_DESC_DBF = DBF_DIR / "pro_desc.dbf"
EXISTE_DBF = DBF_DIR / "existe.dbf"
PRECIPROD_DBF = DBF_DIR / "PRECIPROD.DBF"

# ============================================================================
# FILTERS & BATCH SIZES
# ============================================================================

# Productos bloqueados (IDs que no se sincronizan)
PRODUCTOS_BLOQUEADOS = {'99999', '99998', '100', '99'}

# Categoría bloqueada
CATEGORIA_BLOQUEADA = 'GASTOS'

# Registros por lote en modo multithread batch
BATCH_SIZE = {
    "categorias": 100,
    "productos": 500,
    "listas": 100,
    "items": 2000,
    "users": 200,
}
