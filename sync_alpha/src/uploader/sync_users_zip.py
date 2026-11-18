"""
Sincronización GZIP de Vendedores y Clientes (DBF -> /sync-upload/*).
"""

from datetime import datetime

from ..config import ADMIN_PASSWORD, ADMIN_USERNAME, AGENTES_DBF, BACKEND_URL, CLIENTES_DBF
from ..extractors import load_customers_dataframe, load_sellers_dataframe
from ..transformers import build_customer_dict, build_seller_dict
from .api_client import login, upload_compressed_json


def run_sellers_sync(token: str, sync_time: str | None = None):
    """Lee agentes.dbf y sube vendedores comprimidos en GZIP."""
    print("\n--- SELLERS (AGENTS) ---")
    df_agents = load_sellers_dataframe(AGENTES_DBF, encoding="latin1")

    sellers_list = []
    if df_agents is not None and not df_agents.empty and "CVE_AGE" in df_agents.columns:
        for _, row in df_agents.iterrows():
            try:
                sellers_list.append(build_seller_dict(row, sync_time))
            except Exception:
                continue

    if sellers_list:
        upload_compressed_json("/sync-upload/sellers-json", {"sellers": sellers_list}, token)
    else:
        print("  No sellers found.")


def run_customers_sync(token: str, sync_time: str | None = None):
    """Lee clientes.dbf y sube clientes comprimidos en GZIP."""
    print("\n--- CUSTOMERS ---")
    df_cust = load_customers_dataframe(CLIENTES_DBF, encoding="latin1")

    customers_list = []
    if df_cust is not None and not df_cust.empty and "CVE_CTE" in df_cust.columns:
        for _, row in df_cust.iterrows():
            try:
                customers_list.append(build_customer_dict(row, sync_time))
            except Exception:
                continue

    if customers_list:
        upload_compressed_json("/sync-upload/customers-json", {"customers": customers_list}, token)
    else:
        print("  No customers found.")


def main():
    start = datetime.now()
    print(f"STARTING USERS ZIP SYNC {start}")

    token = login(BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    if not token:
        return

    try:
        run_sellers_sync(token)
        run_customers_sync(token)
    except Exception as exc:
        print(f"\nCRITICAL FAILURE: {exc}")
        import traceback
        traceback.print_exc()

    end = datetime.now()
    print(f"\nCOMPLETED IN {(end - start).total_seconds():.2f}s")


if __name__ == "__main__":
    main()
