"""
Data Cleaning - Funciones de normalización y limpieza de datos DBF.
"""

import re
import unicodedata
import pandas as pd


def clean_text(value):
    """Limpia strings eliminando espacios sobrantes y retorna None si queda vacío."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return str(value).strip()


def normalize_text(text):
    """Quita acentos y convierte a mayúsculas."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.upper()


def clean_name(name):
    """Normaliza un nombre eliminando paréntesis y caracteres especiales."""
    name = normalize_text(name)
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def clean_number(value, default=0.0):
    """Convierte un valor a float de forma segura."""
    if pd.isna(value) or value == "":
        return default
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return default


def clean_digits(value):
    """Elimina todo excepto dígitos numéricos."""
    if not value or str(value).lower() == "nan":
        return ""
    return re.sub(r"\D", "", str(value))


def clean_lada(lada):
    """Limpia código de área (lada) mexicana."""
    lada = clean_digits(lada)
    if lada.startswith(("044", "045")):
        lada = lada[3:]
    elif lada.startswith("01"):
        lada = lada[2:]

    if lada.isdigit() and len(lada) in (2, 3):
        return lada
    return ""


def build_phone(lada, number):
    """Construye teléfono en formato internacional +52XXXXXXXXXX."""
    number = clean_digits(number)
    lada = clean_lada(lada)

    if len(number) == 10:
        return f"+52{number}"

    if len(number) == 8 and lada:
        return f"+52{lada}{number}"

    return None


def build_username(name, customer_id):
    """Crea un username único y válido para el cliente."""
    legal_suffixes = [
        "S DE RL DE CV", "S DE RL", "S DE R L", "S DE R.L",
        "SA DE CV", "S A DE C V", "S.A. DE C.V.",
        "SA", "S.A.", "DE CV", "SOCIEDAD",
    ]

    base = clean_name(name).lower()

    for suffix in legal_suffixes:
        suffix_with_space = " " + suffix.lower()
        if base.endswith(suffix_with_space):
            base = base[:-len(suffix_with_space)].strip()
            break

    base = base.replace(" ", "_")
    base = base[:50].rstrip("_")

    if not base:
        base = "CLIENTE"

    return f"{base}_{customer_id}"


# Alias retrocompatibles
limpiar_texto = clean_text
normalizar_texto = normalize_text
limpiar_nombre = clean_name
limpiar_numero = clean_number
limpiar_digitos = clean_digits
limpiar_lada = clean_lada
construir_telefono = build_phone
crear_username = build_username
