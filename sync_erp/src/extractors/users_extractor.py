"""
Extractor de Clientes (dbo.socios) y Vendedores/Agentes desde SQL Server 2000.
"""

import pandas as pd
from ..database import query_to_dataframe


def get_customers_dataframe() -> pd.DataFrame:
    """
    Extrae el padrón de clientes desde dbo.socios.
    Filtra los registros marcados como borrados (BORRADO = 1).
    """
    sql = """
        SELECT 
            NUMERO AS "NUMERO",
            RTRIM(LTRIM(NOMBRE)) AS "NOMBRE",
            RTRIM(LTRIM(TELEFONO)) AS "TELEFONO",
            RTRIM(LTRIM(CALLE)) AS "CALLE",
            RTRIM(LTRIM(NUMEXT)) AS "NUMEXT",
            RTRIM(LTRIM(NUMINT)) AS "NUMINT",
            RTRIM(LTRIM(COLONIA)) AS "COLONIA",
            RTRIM(LTRIM(CIUDAD)) AS "CIUDAD",
            RTRIM(LTRIM(ESTADO)) AS "ESTADO",
            RTRIM(LTRIM(CP)) AS "CP",
            RTRIM(LTRIM(RFC)) AS "RFC",
            RTRIM(LTRIM(EMAIL)) AS "EMAIL",
            RTRIM(LTRIM(EMAIL2)) AS "EMAIL2",
            RTRIM(LTRIM(EMAIL3)) AS "EMAIL3",
            BORRADO AS "BORRADO",
            VENDEDOR AS "VENDEDOR",
            PRECIO AS "PRECIO"
        FROM dbo.socios
        WHERE NUMERO IS NOT NULL 
          AND NUMERO > 0
          AND (BORRADO IS NULL OR BORRADO = 0)
        ORDER BY NUMERO ASC
    """
    return query_to_dataframe(sql)


def get_sellers_dataframe() -> pd.DataFrame:
    """
    Extrae los vendedores / agentes desde dbo.empleado en SQL Server 2000.
    Filtra los empleados marcados como borrados (BORRADO = 1).
    """
    sql = """
        SELECT 
            NUMERO AS "NUMERO",
            RTRIM(LTRIM(NOMBRE)) AS "NOMBRE",
            RTRIM(LTRIM(TELEFONO)) AS "TELEFONO",
            RTRIM(LTRIM(RFC)) AS "RFC",
            RTRIM(LTRIM([USER])) AS "USER",
            RTRIM(LTRIM(DIREC)) AS "DIREC",
            RTRIM(LTRIM(CIUDAD)) AS "CIUDAD",
            BORRADO AS "BORRADO",
            TIPO AS "TIPO",
            ZONA AS "ZONA",
            PORCVTA AS "PORCVTA"
        FROM dbo.empleado
        WHERE NUMERO IS NOT NULL 
          AND NUMERO > 0
          AND (BORRADO IS NULL OR BORRADO = 0)
        ORDER BY NUMERO ASC
    """
    return query_to_dataframe(sql)
