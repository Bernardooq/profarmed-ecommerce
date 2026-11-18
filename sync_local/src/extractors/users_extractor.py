"""Extractor de vendedores (agentes.dbf) y clientes (clientes.dbf)."""

from pathlib import Path
from ..config import AGENTES_DBF, CLIENTES_DBF
from .dbf_reader import dbf_to_dataframe


def load_sellers_dataframe(dbf_path: Path = AGENTES_DBF, encoding: str = "latin1"):
    """Lee agentes.dbf filtrando registros con CVE_AGE válido."""
    if not dbf_path.exists():
        print(f"Warning: {dbf_path.name} not found")
        return None
    df_agents = dbf_to_dataframe(dbf_path, encoding=encoding)
    if not df_agents.empty and "CVE_AGE" in df_agents.columns:
        return df_agents[df_agents["CVE_AGE"].notna()].copy()
    return df_agents


def load_customers_dataframe(dbf_path: Path = CLIENTES_DBF, encoding: str = "latin1"):
    """Lee clientes.dbf filtrando registros con CVE_CTE válido."""
    if not dbf_path.exists():
        print(f"Warning: {dbf_path.name} not found")
        return None
    df_cust = dbf_to_dataframe(dbf_path, encoding=encoding)
    if not df_cust.empty and "CVE_CTE" in df_cust.columns:
        return df_cust[df_cust["CVE_CTE"].notna()].copy()
    return df_cust
