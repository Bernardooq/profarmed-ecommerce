"""Utilidades base para lectura de archivos Visual FoxPro (DBF)."""

from pathlib import Path
import pandas as pd
from dbfread import DBF


def dbf_to_dataframe(dbf_path: Path, encoding: str = "latin1") -> pd.DataFrame:
    """Lee un archivo DBF y retorna un DataFrame de pandas."""
    print(f"Reading {dbf_path.name}...")
    dbf = DBF(dbf_path, encoding=encoding, ignore_missing_memofile=True)
    return pd.DataFrame(iter(dbf))
