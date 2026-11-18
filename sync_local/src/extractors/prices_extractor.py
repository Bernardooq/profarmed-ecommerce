"""Extractor de listas de precios e items desde PRECIPROD.DBF."""

from pathlib import Path
from ..config import PRECIPROD_DBF
from .dbf_reader import dbf_to_dataframe


def load_price_items_dataframe(dbf_path: Path = PRECIPROD_DBF):
    """Lee PRECIPROD.DBF y retorna el DataFrame completo."""
    return dbf_to_dataframe(dbf_path)
