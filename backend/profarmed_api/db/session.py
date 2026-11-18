"""
Configuracion de la sesion de base de datos para PROFARMED

Este modulo configura el motor de SQLAlchemy y el creador de sesiones
que se utilizara en toda la aplicacion para interactuar con PostgreSQL.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from core.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Sanitizar y normalizar URL de base de datos
db_url = (DATABASE_URL or "").strip()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Conmutación inteligente a Transaction Pooler para Supabase:
# En Supabase:
# - Puerto 5432 es "Session Mode" (límite duro de 15 conexiones = EMAXCONNSESSION).
# - Puerto 6543 es "Transaction Mode", diseñado para FastAPI y servidores web concurrentes.
force_session_mode = os.getenv("SUPABASE_FORCE_SESSION_MODE", "false").lower() in ("true", "1", "yes")
if not force_session_mode and "pooler.supabase.com:5432" in db_url:
    db_url = db_url.replace("pooler.supabase.com:5432", "pooler.supabase.com:6543")
    logger.info("[DB] Supabase pooler detectado: conmutado a Transaction Mode (puerto 6543) para prevenir EMAXCONNSESSION.")

# Configuración de pool de conexiones optimizado para alta concurrencia
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))
use_nullpool = os.getenv("DB_USE_NULLPOOL", "false").lower() in ("true", "1", "yes")

engine_kwargs = {
    "pool_pre_ping": True,
}

if use_nullpool:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = DB_POOL_SIZE
    engine_kwargs["max_overflow"] = DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = DB_POOL_TIMEOUT
    engine_kwargs["pool_recycle"] = DB_POOL_RECYCLE

# Argumentos de conexión específicos para PostgreSQL / Supabase
connect_args = {}
if "supabase.com" in db_url:
    connect_args["connect_timeout"] = 10
    connect_args["application_name"] = "profarmed_api"

if connect_args:
    engine_kwargs["connect_args"] = connect_args

# Motor de base de datos con pool adaptativo
engine = create_engine(
    db_url,
    **engine_kwargs
)

# Fabrica de sesiones de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
