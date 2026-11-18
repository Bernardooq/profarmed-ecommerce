"""
Pipeline de Sincronización ERP: PRODUCTOS, CATEGORÍAS Y LISTAS DE PRECIOS.
"""

from datetime import datetime
import sys
from pathlib import Path

# Permitir ejecucion directa como script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import IMAGES_FOLDER, CDN_URL
from src.extractors import (
    get_products_dataframe,
    get_extra_descriptions,
    get_stock_map,
    get_price_lists_dataframe,
    get_price_items_dataframe
)
from src.transformers import (
    build_producto_dict,
    build_lista_precios_dict,
    build_item_lista_dict,
    limpiar_texto
)
from src.uploader.api_client import (
    login,
    upload_compressed_json,
    cleanup_non_synced,
    verificar_imagen_existe
)


def run_products_sync(token: str, sync_time: str):
    print("\n--- PASO 1: EXTRACCIÓN Y SINCRONIZACIÓN DE PRODUCTOS ---")
    df_prod = get_products_dataframe()
    descripciones = get_extra_descriptions()
    stock_map = get_stock_map()
    
    print(f"  Total productos a sincronizar: {len(df_prod)}")
    
    productos_list = []
    categorias = set()
    
    def check_img(codebar_val, fallback_id=None):
        return verificar_imagen_existe(
            codebar_val,
            IMAGES_FOLDER,
            CDN_URL,
            fallback_id=fallback_id,
        )

    for _, row in df_prod.iterrows():
        pid = limpiar_texto(row.get('CVE_PROD'))
        if not pid:
            continue

        cat = limpiar_texto(row.get('CSE_PROD'))
        if cat:
            categorias.add(cat)

        productos_list.append(build_producto_dict(row, descripciones, stock_map, check_img, sync_time))

    with_img = sum(1 for p in productos_list if p.get("image_url"))
    print(f"  Imágenes resueltas ({IMAGES_FOLDER}): {with_img} con portada, {len(productos_list) - with_img} sin imagen")

    payload = {"categorias": sorted(list(categorias)), "productos": productos_list}
    upload_compressed_json("/sync-upload/productos-json", payload, token)


def run_pricelists_sync(token: str, sync_time: str):
    print("\n--- PASO 2: LISTAS DE PRECIOS (CABECERAS) ---")
    df = get_price_lists_dataframe()
    if df.empty:
        print("  No se encontraron listas de precios.")
        return
        
    unique_ids = df['NLISPRE'].dropna().unique()
    listas_payload = []
    for lis_id in unique_ids:
        if not lis_id:
            continue
        try:
            listas_payload.append(build_lista_precios_dict(lis_id, sync_time))
        except (ValueError, TypeError):
            continue
            
    payload = {"listas": listas_payload}
    upload_compressed_json("/sync-upload/listas-precios-json", payload, token)


def run_price_items_sync(token: str, sync_time: str):
    print("\n--- PASO 3: RENGLONES DE PRECIOS POR PRODUCTO ---")
    df = get_price_items_dataframe()
    if df.empty:
        print("  No se encontraron renglones de precios.")
        return
        
    items_payload = []
    for _, row in df.iterrows():
        pid = limpiar_texto(row.get('CVE_PROD'))
        lis_id = limpiar_texto(row.get('NLISPRE'))
        if not pid or not lis_id:
            continue
        items_payload.append(build_item_lista_dict(row, sync_time))
        
    payload = {"items": items_payload}
    upload_compressed_json("/sync-upload/items-precios-json", payload, token)


def main():
    start = datetime.now()
    sync_time = start.isoformat()
    print("=" * 60)
    print(f"INICIANDO SINCRONIZACIÓN DE CATÁLOGO Y PRECIOS ERP: {start}")
    print("=" * 60)
    
    token = login()
    if not token:
        print("[CRITICAL] Abortando por fallo de autenticación.")
        sys.exit(1)
        
    try:
        run_products_sync(token, sync_time)
        run_pricelists_sync(token, sync_time)
        run_price_items_sync(token, sync_time)
        cleanup_non_synced(token, start)
    except Exception as e:
        print(f"\n[CRITICAL FAILURE]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    end = datetime.now()
    duration = (end - start).total_seconds()
    print("=" * 60)
    print(f"PROCESO DE CATÁLOGO FINALIZADO CON ÉXITO EN {duration:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()

