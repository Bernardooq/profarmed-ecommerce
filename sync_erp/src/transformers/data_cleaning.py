"""
Data Cleaning - Funciones de normalización y limpieza de datos para ERP Sync.
"""

import re
import unicodedata
import pandas as pd


# ============================================================================
# LIMPIEZA DE TEXTO
# ============================================================================

def limpiar_texto(valor):
    """Limpia strings eliminando espacios sobrantes, valores nulos y NaN."""
    if valor is None or pd.isna(valor):
        return None
    s = str(valor).strip()
    if not s or s.lower() in ('nan', 'none', 'null'):
        return None
    return s


def normalizar_texto(texto):
    """Quita acentos y convierte a mayúsculas para comparaciones o índices."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.upper()


def limpiar_nombre(nombre):
    """Limpia un nombre eliminando paréntesis y caracteres especiales."""
    nombre = normalizar_texto(nombre)
    nombre = re.sub(r"\(.*?\)", "", nombre)
    nombre = re.sub(r"[^\w\s]", " ", nombre)
    nombre = re.sub(r"\s+", " ", nombre).strip()
    return nombre


# ============================================================================
# LIMPIEZA DE NÚMEROS
# ============================================================================

def limpiar_numero(valor, default=0.0):
    """Convierte a número float de forma segura."""
    if pd.isna(valor) or valor == '' or valor is None:
        return default
    try:
        s = str(valor).replace(",", "").strip()
        if not s or s.lower() in ('nan', 'none', 'null'):
            return default
        return float(s)
    except Exception:
        return default


def safe_int(valor, default=None):
    """Convierte a entero de forma segura evitando excepciones con NaN, None o strings."""
    if valor is None or pd.isna(valor):
        return default
    try:
        s = str(valor).strip().lower()
        if not s or s in ('nan', 'none', 'null'):
            return default
        return int(float(s))
    except (ValueError, TypeError, OverflowError):
        return default


# ============================================================================
# TELÉFONOS
# ============================================================================

def limpiar_digitos(valor):
    """Quita todo excepto dígitos numéricos."""
    if not valor or str(valor).lower() == 'nan':
        return ""
    return re.sub(r"\D", "", str(valor))


def limpiar_lada(lada):
    """Limpia código de área (lada) mexicana quitando prefijos 01/044/045."""
    lada = limpiar_digitos(lada)
    if lada.startswith(("044", "045")):
        lada = lada[3:]
    elif lada.startswith("01"):
        lada = lada[2:]
    
    if lada.isdigit() and len(lada) in (2, 3):
        return lada
    return ""


def construir_telefono(lada, numero):
    """Construye teléfono en formato internacional +52XXXXXXXXXX."""
    numero = limpiar_digitos(numero)
    lada = limpiar_lada(lada)
    
    if len(numero) == 10:
        return f"+52{numero}"
    if len(numero) == 8 and lada:
        return f"+52{lada}{numero}"
    return None


# ============================================================================
# USERNAMES
# ============================================================================

def crear_username(nombre, id_cliente):
    """Crea un username único y seguro para clientes de B2B."""
    PALABRAS_LEGALES = [
        "S DE RL DE CV", "S DE RL", "S DE R L", "S DE R.L",
        "SA DE CV", "S A DE C V", "S.A. DE C.V.",
        "SA", "S.A.", "DE CV", "SOCIEDAD"
    ]
    
    base = limpiar_nombre(nombre).lower()
    
    for palabra in PALABRAS_LEGALES:
        palabra_con_espacio = " " + palabra.lower()
        if base.endswith(palabra_con_espacio):
            base = base[:-len(palabra_con_espacio)].strip()
            break
        elif base == palabra:
            pass
    
    base = base.replace(" ", "_")
    base = base[:50].rstrip("_")
    
    if not base:
        base = "CLIENTE"
    
    return f"{base}_{id_cliente}"

