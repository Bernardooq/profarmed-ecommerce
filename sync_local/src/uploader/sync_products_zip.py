"""
Sincronización GZIP de Catálogo y Listas de Precios (DBF -> /sync-upload/*).
"""

from datetime import datetime, timedelta

from ..config import ADMIN_PASSWORD, ADMIN_USERNAME, BACKEND_URL, PRECIPROD_DBF, PRODUCTO_DBF, PRO_DESC_DBF, EXISTE_DBF
from ..extractors import (
    load_extra_descriptions,
    load_price_items_dataframe,
    load_products_dataframe,
    load_stock_map,
)
from ..transformers import (
    build_pricelist_dict,
    build_pricelist_item_dict,
    build_product_dict,
    clean_text,
)
from .api_client import (
    cleanup_non_synced,
    login,
    upload_compressed_json,
    verify_product_image,
)


def run_products_sync(token: str, sync_time: str):
    """Lee productos, descripciones y existencias, y sube el payload GZIP."""
    print("\n--- STEP 1: PRODUCTS ---")
    df_prod = load_products_dataframe(PRODUCTO_DBF, apply_filters=True)
    descriptions_map = load_extra_descriptions(PRO_DESC_DBF)
    stock_map = load_stock_map(EXISTE_DBF)

    products_list = []
    categories = set()

    for _, row in df_prod.iterrows():
        pid = clean_text(row.get("CVE_PROD"))
        if not pid:
            continue

        category = clean_text(row.get("CSE_PROD"))
        if category:
            categories.add(category)

        products_list.append(
            build_product_dict(row, descriptions_map, stock_map, verify_product_image, sync_time)
        )

    payload = {"categorias": list(categories), "productos": products_list}
    upload_compressed_json("/sync-upload/productos-json", payload, token)


def run_pricelists_sync(token: str, sync_time: str):
    """Lee encabezados únicos de listas de precios desde PRECIPROD.DBF y los sube."""
    print("\n--- STEP 2: PRICE LISTS (HEADERS) ---")
    df_prices = load_price_items_dataframe(PRECIPROD_DBF)
    unique_ids = df_prices["NLISPRE"].unique()

    lists_payload = []
    for list_id in unique_ids:
        if not list_id:
            continue
        try:
            lists_payload.append(build_pricelist_dict(list_id, sync_time))
        except ValueError:
            continue

    upload_compressed_json("/sync-upload/listas-precios-json", {"listas": lists_payload}, token)


def run_price_items_sync(token: str, sync_time: str):
    """Lee items de listas de precios desde PRECIPROD.DBF y los sube en GZIP."""
    print("\n--- STEP 3: PRICE LIST ITEMS ---")
    df_prices = load_price_items_dataframe(PRECIPROD_DBF)

    items_payload = []
    for _, row in df_prices.iterrows():
        pid = clean_text(row.get("CVE_PROD"))
        list_id = clean_text(row.get("NLISPRE"))
        if not pid or not list_id:
            continue
        items_payload.append(build_pricelist_item_dict(row, sync_time))

    upload_compressed_json("/sync-upload/items-precios-json", {"items": items_payload}, token)


def main():
    start = datetime.now()
    print(f"STARTING PRODUCTS ZIP SYNC {start}")
    sync_time = start.isoformat()

    token = login(BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    if not token:
        return

    try:
        run_products_sync(token, sync_time)
        run_pricelists_sync(token, sync_time)
        run_price_items_sync(token, sync_time)

        # Restamos 5 minutos para dar margen al procesamiento de la cola en background
        cleanup_time = (start - timedelta(minutes=5)).isoformat()
        cleanup_non_synced(token, cleanup_time)
    except Exception as exc:
        print(f"\nCRITICAL FAILURE: {exc}")
        import traceback
        traceback.print_exc()

    end = datetime.now()
    print(f"\nCOMPLETED IN {(end - start).total_seconds():.2f}s")


if __name__ == "__main__":
    main()
