"""
Pipeline Maestro Consolidado: Sincroniza Catálogo, Precios y Usuarios en una sola corrida.
"""

from datetime import datetime
import sys
from pathlib import Path

# Permitir ejecucion directa como script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.uploader.api_client import login, cleanup_non_synced
from src.uploader.sync_products import run_products_sync, run_pricelists_sync, run_price_items_sync
from src.uploader.sync_users import run_sellers_sync, run_customers_sync


def main():
    start = datetime.now()
    sync_time = start.isoformat()
    print("*" * 65)
    print(f"SINCRONIZACIÓN COMPLETA ERP (PRODUCTOS + PRECIOS + USUARIOS)")
    print(f"Inicio: {start}")
    print("*" * 65)
    
    token = login()
    if not token:
        print("[CRITICAL] Fallo de autenticación. Abortando.")
        sys.exit(1)
        
    try:
        # 1. Catálogo de productos
        run_products_sync(token, sync_time)
        
        # 2. Listas de precios
        run_pricelists_sync(token, sync_time)
        run_price_items_sync(token, sync_time)
        
        # 3. Usuarios
        run_sellers_sync(token, sync_time)
        run_customers_sync(token, sync_time)
        
        # 4. Limpieza de catálogo
        cleanup_non_synced(token, start)
    except Exception as e:
        print(f"\n[CRITICAL FAILURE EN SYNC ALL]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    end = datetime.now()
    total_sec = (end - start).total_seconds()
    print("*" * 65)
    print(f"SINCRONIZACIÓN COMPLETA FINALIZADA EXITOSAMENTE EN {total_sec:.2f}s")
    print("*" * 65)


if __name__ == "__main__":
    main()

