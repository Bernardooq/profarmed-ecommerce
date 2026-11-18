"""
Sincronización Unificada Secuencial por Lotes (DBF -> /sync/*).

Orden de ejecución:
1. Categorías
2. Productos
3. Listas de precios
4. Items de listas
5. Vendedores
6. Clientes
7. Cleanup global (productos y usuarios)
"""

from datetime import datetime, timezone

from ..config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    AGENTES_DBF,
    BACKEND_URL,
    BATCH_SIZE,
    CLIENTES_DBF,
    EXISTE_DBF,
    PRECIPROD_DBF,
    PRODUCTO_DBF,
    PRO_DESC_DBF,
)
from ..extractors import (
    load_customers_dataframe,
    load_extra_descriptions,
    load_price_items_dataframe,
    load_products_dataframe,
    load_sellers_dataframe,
    load_stock_map,
)
from ..transformers import (
    build_category_dict,
    build_customer_dict,
    build_pricelist_dict,
    build_pricelist_item_dict,
    build_product_dict,
    build_seller_dict,
    clean_text,
)
from .api_client import (
    cleanup_non_synced,
    cleanup_non_synced_users,
    login,
    sync_in_parallel,
    verify_product_image,
)


def main():
    start_total = datetime.now()
    sync_time = datetime.now(timezone.utc).isoformat()

    print(f"=== UNIFIED SEQUENTIAL BATCH SYNC START: {start_total} ===")
    print(f"=== SYNC TIMESTAMP: {sync_time} ===")

    token = login(BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    if not token:
        return

    # Step 1: Categories
    print("\n--- STEP 1: CATEGORIES ---")
    df_prod = load_products_dataframe(PRODUCTO_DBF, apply_filters=True)
    if not df_prod.empty:
        cats_uniq = df_prod["CSE_PROD"].dropna().apply(clean_text).unique()
        cats_data = [build_category_dict(c, sync_time) for c in cats_uniq if c]
        sync_in_parallel(cats_data, BATCH_SIZE["categorias"], "sync/categories", token, "Categories", max_workers=1)

    # Step 2: Products
    print("\n--- STEP 2: PRODUCTS ---")
    if not df_prod.empty:
        stock_map = load_stock_map(EXISTE_DBF)
        desc_map = load_extra_descriptions(PRO_DESC_DBF)

        products_list = []
        for _, row in df_prod.iterrows():
            pid = clean_text(row.get("CVE_PROD"))
            if not pid:
                continue
            products_list.append(
                build_product_dict(row, desc_map, stock_map, verify_product_image, sync_time)
            )
        sync_in_parallel(products_list, BATCH_SIZE["productos"], "sync/products", token, "Products", max_workers=8)

    # Step 3: Price Lists
    print("\n--- STEP 3: PRICE LISTS ---")
    df_price = load_price_items_dataframe(PRECIPROD_DBF)
    if not df_price.empty:
        lids = df_price["NLISPRE"].dropna().unique()
        lists_data = [build_pricelist_dict(i, sync_time) for i in lids if i]
        sync_in_parallel(lists_data, BATCH_SIZE["listas"], "sync/price-lists", token, "PriceLists", max_workers=1)

    # Step 4: Price Items
    print("\n--- STEP 4: PRICE ITEMS ---")
    if not df_price.empty:
        items_data = []
        for _, row in df_price.iterrows():
            pid = clean_text(row.get("CVE_PROD"))
            lid = clean_text(row.get("NLISPRE"))
            if pid and lid:
                items_data.append(build_pricelist_item_dict(row, sync_time))
        sync_in_parallel(items_data, BATCH_SIZE["items"], "sync/price-list-items", token, "PriceItems", max_workers=10)

    # Step 5: Sellers
    print("\n--- STEP 5: SELLERS ---")
    df_agents = load_sellers_dataframe(AGENTES_DBF, encoding="latin1")
    if df_agents is not None and not df_agents.empty and "CVE_AGE" in df_agents.columns:
        sellers_list = []
        for _, row in df_agents.iterrows():
            try:
                sellers_list.append(build_seller_dict(row, sync_time))
            except Exception:
                continue
        sync_in_parallel(sellers_list, BATCH_SIZE["users"], "sync/sellers", token, "Sellers", max_workers=1)

    # Step 6: Customers
    print("\n--- STEP 6: CUSTOMERS ---")
    df_cust = load_customers_dataframe(CLIENTES_DBF, encoding="latin1")
    if df_cust is not None and not df_cust.empty and "CVE_CTE" in df_cust.columns:
        customers_list = []
        for _, row in df_cust.iterrows():
            try:
                customers_list.append(build_customer_dict(row, sync_time))
            except Exception:
                continue
        sync_in_parallel(customers_list, BATCH_SIZE["users"], "sync/customers", token, "Customers", max_workers=5)

    # Step 7: Cleanup
    cleanup_non_synced(token, sync_time)
    cleanup_non_synced_users(token, sync_time)

    end_total = datetime.now()
    print(f"\n{'=' * 60}")
    print(f"ALL SYNC OPERATIONS COMPLETED IN {(end_total - start_total).total_seconds():.2f}s")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
