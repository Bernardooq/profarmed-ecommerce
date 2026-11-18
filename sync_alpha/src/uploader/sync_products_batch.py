"""
Sincronización Multithread por Lotes de Catálogo y Listas de Precios (DBF -> /sync/*).
"""

from datetime import datetime, timezone

from ..config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    BACKEND_URL,
    BATCH_SIZE,
    CATEGORIA_BLOQUEADA,
    EXISTE_DBF,
    PRECIPROD_DBF,
    PRODUCTOS_BLOQUEADOS,
    PRODUCTO_DBF,
    PRO_DESC_DBF,
)
from ..extractors import (
    filter_active_products,
    load_extra_descriptions,
    load_price_items_dataframe,
    load_products_dataframe,
    load_stock_map,
)
from ..transformers import (
    build_category_dict,
    build_pricelist_dict,
    build_pricelist_item_dict,
    build_product_dict,
    clean_text,
)
from .api_client import cleanup_non_synced, login, sync_in_parallel, verify_product_image


def build_categories_payload(df_products, sync_time):
    """Extrae categorías únicas válidas."""
    categories = df_products["CSE_PROD"].dropna().apply(clean_text).unique()
    valid = [
        cat for cat in categories
        if cat and cat.upper() != CATEGORIA_BLOQUEADA and cat not in PRODUCTOS_BLOQUEADOS
    ]
    return [build_category_dict(cat, sync_time) for cat in valid]


def build_products_payload(df_products, descriptions_map, stock_map, sync_time):
    """Prepara lista de productos filtrados para envío por lotes."""
    print("Processing products...")
    products = []
    for _, row in filter_active_products(df_products).iterrows():
        pid = clean_text(row.get("CVE_PROD"))
        if not pid:
            continue
        products.append(
            build_product_dict(row, descriptions_map, stock_map, verify_product_image, sync_time)
        )
    return products


def run_products_batch_sync(token: str, sync_time: str):
    """Sincroniza categorías, productos, listas de precios e items por lotes paralelos."""
    descriptions_map = load_extra_descriptions(PRO_DESC_DBF)
    stock_map = load_stock_map(EXISTE_DBF)

    df_products = load_products_dataframe(PRODUCTO_DBF, apply_filters=False)
    df_products = df_products.map(lambda x: clean_text(x) if isinstance(x, str) else x)
    df_prices = load_price_items_dataframe(PRECIPROD_DBF)

    print()
    categories = build_categories_payload(df_products, sync_time)
    sync_in_parallel(categories, BATCH_SIZE["categorias"], "sync/categories", token, "Categorías", max_workers=5, verbose_errors=True)

    products = build_products_payload(df_products, descriptions_map, stock_map, sync_time)
    sync_in_parallel(products, BATCH_SIZE["productos"], "sync/products", token, "Productos", max_workers=8, verbose_errors=True)

    list_ids = df_prices["NLISPRE"].dropna().apply(clean_text).unique()
    pricelists = [build_pricelist_dict(lid, sync_time) for lid in list_ids if lid]
    sync_in_parallel(pricelists, BATCH_SIZE["listas"], "sync/price-lists", token, "Listas de Precios", max_workers=5, verbose_errors=True)

    print("Processing price list items...")
    items = []
    for _, row in df_prices.iterrows():
        pid = clean_text(row.get("CVE_PROD"))
        lid = clean_text(row.get("NLISPRE"))
        if pid and lid:
            items.append(build_pricelist_item_dict(row, sync_time))
    sync_in_parallel(items, BATCH_SIZE["items"], "sync/price-list-items", token, "Items de Listas", max_workers=10, verbose_errors=True)


def main():
    start = datetime.now(timezone.utc)
    sync_time = start.isoformat()

    print(f"\n{'=' * 60}")
    print(f"DBF Products Batch Sync - {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    token = login(BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    if not token:
        print("Authentication failed. Aborting.\n")
        return

    run_products_batch_sync(token, sync_time)
    cleanup_non_synced(token, sync_time)

    end = datetime.now(timezone.utc)
    print(f"\n{'=' * 60}")
    print(f"Completed in {(end - start).total_seconds():.1f}s")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
