"""
Sincronización GZIP Completa (Catálogo, Precios, Usuarios y Cleanup).
"""

from datetime import datetime, timedelta

from ..config import ADMIN_PASSWORD, ADMIN_USERNAME, BACKEND_URL
from .api_client import cleanup_non_synced, cleanup_non_synced_users, login
from .sync_products_zip import run_price_items_sync, run_pricelists_sync, run_products_sync
from .sync_users_zip import run_customers_sync, run_sellers_sync


def main():
    start = datetime.now()
    print(f"STARTING FULL ZIP SYNC {start}")
    sync_time = start.isoformat()

    token = login(BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    if not token:
        return

    try:
        run_products_sync(token, sync_time)
        run_pricelists_sync(token, sync_time)
        run_price_items_sync(token, sync_time)
        run_sellers_sync(token, sync_time=sync_time)
        run_customers_sync(token, sync_time=None)

        # Margen de 5 minutos para dar tiempo a la cola del backend
        cleanup_time = (start - timedelta(minutes=5)).isoformat()
        cleanup_non_synced(token, cleanup_time)
        cleanup_non_synced_users(token, cleanup_time)
    except Exception as exc:
        print(f"\nCRITICAL FAILURE: {exc}")
        import traceback
        traceback.print_exc()

    end = datetime.now()
    print(f"\nCOMPLETED IN {(end - start).total_seconds():.2f}s")


if __name__ == "__main__":
    main()
