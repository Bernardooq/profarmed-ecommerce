"""
Sincronización Multithread por Lotes de Vendedores y Clientes (DBF -> /sync/*).
"""

from datetime import datetime, timezone

from ..config import ADMIN_PASSWORD, ADMIN_USERNAME, AGENTES_DBF, BACKEND_URL, BATCH_SIZE, CLIENTES_DBF
from ..extractors import load_customers_dataframe, load_sellers_dataframe
from ..transformers import build_customer_dict, build_seller_dict
from .api_client import login, send_batch, sync_in_parallel


def run_sellers_batch_sync(token: str, sync_time: str):
    """Lee agentes.dbf y sincroniza vendedores."""
    print("Syncing sellers...")
    df_agents = load_sellers_dataframe(AGENTES_DBF, encoding="latin-1")
    if df_agents is None or df_agents.empty:
        print("  No sellers to sync\n")
        return

    sellers = []
    for _, row in df_agents.iterrows():
        try:
            sellers.append(build_seller_dict(row, sync_time))
        except Exception:
            continue

    if sellers:
        result = send_batch("sync/sellers", sellers, token, "Sellers")
        print(f"  Done: {result.get('creados', 0)} created, {result.get('actualizados', 0)} updated\n")


def run_customers_batch_sync(token: str, sync_time: str):
    """Lee clientes.dbf y sincroniza clientes en paralelo."""
    print("Syncing customers...")
    df_customers = load_customers_dataframe(CLIENTES_DBF, encoding="latin-1")
    if df_customers is None or df_customers.empty:
        print("  No customers to sync\n")
        return

    customers = []
    for _, row in df_customers.iterrows():
        try:
            customers.append(build_customer_dict(row, sync_time))
        except Exception as exc:
            print(f"  [!] Cliente {row.get('CVE_CTE')} falló: {exc}")
            continue

    if not customers:
        print("  No customers to sync\n")
        return

    sync_in_parallel(
        customers,
        BATCH_SIZE["users"],
        "sync/customers",
        token,
        "Customers",
        max_workers=5,
    )


def main():
    start = datetime.now(timezone.utc)
    sync_time = start.isoformat()

    print(f"\n{'=' * 60}")
    print(f"User Batch Sync - {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    token = login(BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    if not token:
        print("Authentication failed. Aborting.\n")
        return

    run_sellers_batch_sync(token, sync_time)
    run_customers_batch_sync(token, sync_time)

    end = datetime.now(timezone.utc)
    print(f"{'=' * 60}")
    print(f"Completed in {(end - start).total_seconds():.1f}s")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
