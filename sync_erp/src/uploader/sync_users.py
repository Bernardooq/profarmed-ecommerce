"""
Pipeline de Sincronización ERP: USUARIOS (AGENTES/VENDEDORES Y CLIENTES/FARMACIAS).
"""

from datetime import datetime
import sys
from pathlib import Path

# Permitir ejecucion directa como script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.extractors import get_sellers_dataframe, get_customers_dataframe
from src.transformers import build_vendedor_dict, build_cliente_dict
from src.uploader.api_client import login, upload_compressed_json


def run_sellers_sync(token: str, sync_time: str):
    print("\n--- PASO 1: VENDEDORES / AGENTES COMERCIALES ---")
    df_agents = get_sellers_dataframe()
    if df_agents.empty:
        print("  No se encontraron agentes.")
        return
        
    sellers_list = []
    for _, r in df_agents.iterrows():
        try:
            s_dict = build_vendedor_dict(r, sync_time)
            if s_dict:
                sellers_list.append(s_dict)
        except Exception:
            continue
            
    if sellers_list:
        print(f"  Total agentes a subir: {len(sellers_list)}")
        payload = {"sellers": sellers_list}
        upload_compressed_json("/sync-upload/sellers-json", payload, token)
    else:
        print("  Sin agentes procesables.")


def run_customers_sync(token: str, sync_time: str):
    print("\n--- PASO 2: CLIENTES B2B / FARMACIAS ---")
    df_cust = get_customers_dataframe()
    if df_cust.empty:
        print("  No se encontraron clientes.")
        return
        
    customers_list = []
    for _, r in df_cust.iterrows():
        try:
            c_dict = build_cliente_dict(r, sync_time)
            if c_dict:
                customers_list.append(c_dict)
        except Exception:
            continue
            
    if customers_list:
        print(f"  Total clientes a subir: {len(customers_list)}")
        payload = {"customers": customers_list}
        upload_compressed_json("/sync-upload/customers-json", payload, token)
    else:
        print("  Sin clientes procesables.")


def main():
    start = datetime.now()
    sync_time = start.isoformat()
    print("=" * 60)
    print(f"INICIANDO SINCRONIZACIÓN DE USUARIOS ERP: {start}")
    print("=" * 60)
    
    token = login()
    if not token:
        print("[CRITICAL] Abortando por fallo de autenticación.")
        sys.exit(1)
        
    try:
        run_sellers_sync(token, sync_time)
        run_customers_sync(token, sync_time)
    except Exception as e:
        print(f"\n[CRITICAL FAILURE]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    end = datetime.now()
    duration = (end - start).total_seconds()
    print("=" * 60)
    print(f"PROCESO DE USUARIOS FINALIZADO CON ÉXITO EN {duration:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()

