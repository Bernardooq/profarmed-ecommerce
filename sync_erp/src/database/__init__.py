"""
Módulo de conexión a Base de Datos ERP.
"""
from .connection import (
    get_erp_connection,
    get_erp_cursor,
    get_erp_transaction,
    adapt_sql_placeholders,
    execute_erp_query,
    query_to_dataframe,
)

__all__ = [
    "get_erp_connection",
    "get_erp_cursor",
    "get_erp_transaction",
    "adapt_sql_placeholders",
    "execute_erp_query",
    "query_to_dataframe",
]

