"""
Extractor de Listas de Precios e Items de Precios desde SQL Server 2000 (dbo.articulo).
Descompone las 6 columnas de precios (PRECIO..PRECIO6) y utilidades (UTI1..UTI6) en renglones de lista.
"""

import pandas as pd
from ..database import query_to_dataframe


def get_price_lists_dataframe() -> pd.DataFrame:
    """
    Retorna las 6 listas de precios estándar que maneja el ERP de Profarmed.
    """
    return pd.DataFrame([
        {"NLISPRE": 1, "list_name": "Lista 1"},
        {"NLISPRE": 2, "list_name": "Lista 2"},
        {"NLISPRE": 3, "list_name": "Lista 3"},
        {"NLISPRE": 4, "list_name": "Lista 4"},
        {"NLISPRE": 5, "list_name": "Lista 5"},
        {"NLISPRE": 6, "list_name": "Lista 6"}
    ])


def get_price_items_dataframe() -> pd.DataFrame:
    """
    Extrae los renglones de precio por producto para las 6 listas desde dbo.articulo.
    Filtra precios en cero o artículos borrados para no generar registros basura.
    """
    sql = """
        SELECT 1 AS "NLISPRE", RTRIM(LTRIM(BARCODE)) AS "CVE_PROD", UTI1 AS "LMARGEN", PRECIO AS "LPRECPROD" 
        FROM dbo.articulo WHERE BARCODE IS NOT NULL AND (BORRADO IS NULL OR BORRADO = 0) AND PRECIO > 0
        UNION ALL
        SELECT 2 AS "NLISPRE", RTRIM(LTRIM(BARCODE)) AS "CVE_PROD", UTI2 AS "LMARGEN", PRECIO2 AS "LPRECPROD" 
        FROM dbo.articulo WHERE BARCODE IS NOT NULL AND (BORRADO IS NULL OR BORRADO = 0) AND PRECIO2 > 0
        UNION ALL
        SELECT 3 AS "NLISPRE", RTRIM(LTRIM(BARCODE)) AS "CVE_PROD", UTI3 AS "LMARGEN", PRECIO3 AS "LPRECPROD" 
        FROM dbo.articulo WHERE BARCODE IS NOT NULL AND (BORRADO IS NULL OR BORRADO = 0) AND PRECIO3 > 0
        UNION ALL
        SELECT 4 AS "NLISPRE", RTRIM(LTRIM(BARCODE)) AS "CVE_PROD", UTI4 AS "LMARGEN", PRECIO4 AS "LPRECPROD" 
        FROM dbo.articulo WHERE BARCODE IS NOT NULL AND (BORRADO IS NULL OR BORRADO = 0) AND PRECIO4 > 0
        UNION ALL
        SELECT 5 AS "NLISPRE", RTRIM(LTRIM(BARCODE)) AS "CVE_PROD", UTI5 AS "LMARGEN", PRECIO5 AS "LPRECPROD" 
        FROM dbo.articulo WHERE BARCODE IS NOT NULL AND (BORRADO IS NULL OR BORRADO = 0) AND PRECIO5 > 0
        UNION ALL
        SELECT 6 AS "NLISPRE", RTRIM(LTRIM(BARCODE)) AS "CVE_PROD", UTI6 AS "LMARGEN", PRECIO6 AS "LPRECPROD" 
        FROM dbo.articulo WHERE BARCODE IS NOT NULL AND (BORRADO IS NULL OR BORRADO = 0) AND PRECIO6 > 0
    """
    return query_to_dataframe(sql)
