"""
Módulo de conexión y ejecución de consultas SQL hacia la base de datos del ERP.
Diseñado para admitir pyodbc, pymssql, psycopg2 o sqlalchemy según el motor del ERP.
"""

from contextlib import contextmanager
import warnings
import pandas as pd
from ..config import (
    ERP_DB_DRIVER, ERP_DB_HOST, ERP_DB_PORT,
    ERP_DB_NAME, ERP_DB_USER, ERP_DB_PASSWORD
)

# Suprimir advertencia de pandas sobre conexiones ODBC directas (DBAPI2)
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*')


def get_erp_connection():
    """
    Retorna una conexión activa hacia la base de datos SQL del ERP.
    Por defecto intenta pyodbc; se adapta automáticamente según el conector configurado.
    """
    try:
        import pyodbc
        server_str = f"{ERP_DB_HOST},{ERP_DB_PORT}" if ERP_DB_PORT and str(ERP_DB_PORT) != "1433" else ERP_DB_HOST
        conn_str = (
            f"DRIVER={{{ERP_DB_DRIVER}}};"
            f"SERVER={server_str};"
            f"DATABASE={ERP_DB_NAME};"
            f"UID={ERP_DB_USER};"
            f"PWD={ERP_DB_PASSWORD};"
        )
        return pyodbc.connect(conn_str, timeout=30)
    except ImportError:
        pass

    try:
        import pymssql
        return pymssql.connect(
            server=ERP_DB_HOST,
            port=ERP_DB_PORT,
            user=ERP_DB_USER,
            password=ERP_DB_PASSWORD,
            database=ERP_DB_NAME,
            as_dict=True,
            timeout=30
        )
    except ImportError:
        pass

    raise RuntimeError(
        "No se encontró un conector SQL instalado (ej. pyodbc, pymssql). "
        "Instala el conector requerido vía pip según el motor de la BD del ERP."
    )


@contextmanager
def get_erp_cursor():
    """Context manager para obtener un cursor SQL y asegurar cierre de conexión."""
    conn = get_erp_connection()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        conn.close()


def query_to_dataframe(sql_query: str, params=None) -> pd.DataFrame:
    """Ejecuta una consulta SQL y retorna los datos en un DataFrame de pandas."""
    conn = get_erp_connection()
    try:
        df = pd.read_sql_query(sql_query, conn, params=params)
        return df
    finally:
        conn.close()


def adapt_sql_placeholders(sql_query: str, paramstyle: str) -> str:
    """Adapta placeholders '?' (pyodbc) a '%s' (pymssql) cuando corresponde."""
    if paramstyle == "%s":
        return sql_query.replace("?", "%s")
    return sql_query


@contextmanager
def get_erp_transaction():
    """
    Context manager transaccional para escrituras atómicas (INSERT/UPDATE/DELETE)
    en SQL Server 2000. Ejecuta COMMIT al salir sin error o ROLLBACK en excepción.
    Retorna (conn, cursor, paramstyle).
    """
    conn = get_erp_connection()
    paramstyle = "%s" if type(conn).__module__.startswith("pymssql") else "?"
    try:
        conn.autocommit = False
    except Exception:
        pass
    cursor = conn.cursor()
    try:
        yield conn, cursor, paramstyle
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def execute_erp_query(sql_query: str, params=None):
    """Ejecuta una consulta SQL y retorna la lista de resultados como diccionarios."""
    with get_erp_cursor() as cursor:
        cursor.execute(sql_query, params or ())
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

