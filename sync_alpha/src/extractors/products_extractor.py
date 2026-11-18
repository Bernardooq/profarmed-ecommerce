"""Extractor de catálogo de productos, descripciones extra y stock desde DBF."""

from pathlib import Path
from dbfread import DBF

from ..config import (
    PRODUCTO_DBF,
    PRO_DESC_DBF,
    EXISTE_DBF,
    CATEGORIA_BLOQUEADA,
    PRODUCTOS_BLOQUEADOS,
)
from ..transformers.data_cleaning import clean_number
from .dbf_reader import dbf_to_dataframe


def filter_active_products(df_prod):
    """Aplica filtros estándar de categoría y productos bloqueados."""
    if df_prod.empty:
        return df_prod

    df_filtered = df_prod[df_prod["CSE_PROD"].astype(str).str.upper().str.strip() != CATEGORIA_BLOQUEADA]
    df_filtered = df_filtered[~df_filtered["CSE_PROD"].astype(str).str.strip().isin(PRODUCTOS_BLOQUEADOS)]
    if "CVE_TIAL" in df_filtered.columns:
        df_filtered = df_filtered[~df_filtered["CVE_TIAL"].astype(str).str.strip().isin(PRODUCTOS_BLOQUEADOS)]
    return df_filtered


def load_products_dataframe(dbf_path: Path = PRODUCTO_DBF, apply_filters: bool = True):
    """Carga producto.dbf y opcionalmente aplica los filtros de exclusión."""
    df_prod = dbf_to_dataframe(dbf_path)
    if not apply_filters:
        return df_prod

    print("Applying filters...")
    initial_count = len(df_prod)
    df_prod = filter_active_products(df_prod)
    print(f"Products: {initial_count} -> {len(df_prod)}")
    return df_prod


def load_extra_descriptions(dbf_path: Path = PRO_DESC_DBF) -> dict:
    """Lee pro_desc.dbf y retorna mapa {producto_id: descripcion_larga}."""
    if not dbf_path.exists():
        print(f"Warning: {dbf_path.name} not found, skipping extra descriptions")
        return {}

    try:
        print("Loading extra descriptions...")
        dbf = DBF(dbf_path, encoding="latin1", ignore_missing_memofile=True)
        return {
            r["CVE_PROD"].strip(): r["DESC1"].strip()
            for r in dbf
            if r.get("CVE_PROD") and r.get("DESC1")
        }
    except Exception as exc:
        print(f"Error reading descriptions: {exc}")
        return {}


def load_stock_map(dbf_path: Path = EXISTE_DBF) -> dict:
    """Lee existe.dbf y retorna mapa acumulado {producto_id: cantidad_en_stock}."""
    if not dbf_path.exists():
        print(f"Warning: {dbf_path.name} not found, stock will default to 0")
        return {}

    try:
        print("Loading stock data...")
        dbf = DBF(dbf_path, encoding="latin1", ignore_missing_memofile=True)

        stock_map = {}
        for row in dbf:
            pid = row.get("CVE_PROD")
            if not pid:
                continue
            pid = pid.strip()

            val = row.get("EXISTENCIA")
            if val is None:
                val = row.get("EXISTE")
            if val is None:
                val = row.get("STOCK")
            if val is None:
                val = 0

            try:
                qty_int = int(float(clean_number(val) or 0))
            except (ValueError, TypeError):
                qty_int = 0

            stock_map[pid] = stock_map.get(pid, 0) + qty_int

        return stock_map
    except Exception as exc:
        print(f"Error reading stock: {exc}")
        return {}


# Alias retrocompatibles
cargar_descripciones_extra = load_extra_descriptions
cargar_existencias = load_stock_map
