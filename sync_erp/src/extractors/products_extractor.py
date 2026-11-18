"""
Extractor de Catálogo de Productos, Descripciones y Stock desde SQL Server 2000 (dbo.articulo, dbo.lineas, dbo.existen).
"""

import pandas as pd
from ..database import query_to_dataframe, execute_erp_query
from ..config import PRODUCTOS_BLOQUEADOS, CATEGORIA_BLOQUEADA


def get_products_dataframe() -> pd.DataFrame:
    """
    Extrae el catálogo maestro de artículos desde dbo.articulo haciendo JOIN con dbo.lineas.
    Filtra artículos borrados. Por defecto la categoría es 'MED'.
    """
    sql = """
        SELECT 
            RTRIM(LTRIM(a.BARCODE)) AS "CVE_PROD",
            RTRIM(LTRIM(a.BARRAS)) AS "CODBAR",
            RTRIM(LTRIM(a.DESCRI)) AS "DESC_PROD",
            'MED' AS "CSE_PROD",
            a.COSTO AS "CTO_ENT",
            CASE WHEN a.EXIVA = 1 THEN 0.0 ELSE COALESCE(a.IVA, 16.0) END AS "PORCENIVA",
            'PZA' AS "UNI_MED",
            a.PRECIO AS "FACT_PESO",
            a.CORRUGADO AS "DATO_4",
            a.LINEA AS "CVE_TIAL",
            RTRIM(LTRIM(l.LINEA)) AS "LINEA_NAME"
        FROM dbo.articulo a
        LEFT JOIN dbo.lineas l ON a.LINEA = l.NUMERO
        WHERE a.BARCODE IS NOT NULL 
          AND RTRIM(LTRIM(a.BARCODE)) <> ''
          AND (a.BORRADO IS NULL OR a.BORRADO = 0)
        ORDER BY a.BARCODE ASC
    """
    df = query_to_dataframe(sql)

    # Filtrar productos o líneas bloqueadas
    if not df.empty and 'CVE_TIAL' in df.columns:
        df = df[~df['CVE_TIAL'].astype(str).str.strip().isin(PRODUCTOS_BLOQUEADOS)]

    return df


def get_extra_descriptions() -> dict:
    """
    Obtiene descripcion_2 que es igual a DESCRI (nombre del producto) desde dbo.articulo.
    """
    sql = """
        SELECT 
            RTRIM(LTRIM(a.BARCODE)) AS "CVE_PROD",
            RTRIM(LTRIM(a.DESCRI)) AS "DESC1"
        FROM dbo.articulo a
        WHERE a.BARCODE IS NOT NULL 
          AND (a.BORRADO IS NULL OR a.BORRADO = 0)
    """
    try:
        rows = execute_erp_query(sql)
        return {str(r['CVE_PROD']).strip(): str(r['DESC1']).strip() for r in rows if r.get('CVE_PROD')}
    except Exception as e:
        print(f"[!] Warning: No se pudieron cargar descripciones secundarias: {e}")
        return {}


def get_stock_map() -> dict:
    """
    Obtiene el stock total agrupado por producto desde dbo.existen.
    Asegura que no se transmitan existencias negativas al storefront.
    """
    sql = """
        SELECT 
            RTRIM(LTRIM(barcode)) AS "CVE_PROD",
            SUM(CANTIDAD) AS "STOCK"
        FROM dbo.existen
        WHERE barcode IS NOT NULL AND RTRIM(LTRIM(barcode)) <> ''
        GROUP BY RTRIM(LTRIM(barcode))
    """
    try:
        rows = execute_erp_query(sql)
        stock_map = {}
        for r in rows:
            pid = str(r.get('CVE_PROD', '')).strip()
            if pid:
                stock_map[pid] = max(0, int(float(r.get('STOCK') or 0)))
        return stock_map
    except Exception as e:
        print(f"[!] Warning: No se pudieron cargar existencias desde dbo.existen: {e}")
        return {}
