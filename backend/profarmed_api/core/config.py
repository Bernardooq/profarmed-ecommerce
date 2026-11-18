"""
CONFIGURACION global de la aplicacion PROFARMED
Incluye CONFIGURACION de:
- Base de datos
- Seguridad y autenticacion
- API y CORS
- Email/SMTP
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Cargar variables de entorno desde el archivo .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):    
    # === CONFIGURACION DE BASE DE DATOS ===
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # === CONFIGURACION DE SEGURIDAD Y JWT ===
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"  # Algoritmo para firmar tokens JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # Duracion de tokens de acceso una jornada laboral
    SYNC_TOKEN_EXPIRE_MINUTES: int = 5  # Duracion de tokens de acceso para sincronizaciones
    
    # === CONFIGURACION DE LA API ===
    PROJECT_NAME: str = "Profarmed API"
    API_V1_STR: str = "/api/v1"
    FRONTEND_URL: str = os.getenv("FRONTEND_URL")
    
    # === CONFIGURACION DE CLOUDFLARE TURNSTILE ===
    TURNSTILE_SECRET_KEY: str = os.getenv("TURNSTILE_SECRET_KEY", "")  # Clave secreta de Turnstile
    
    # === CONFIGURACION DE EMAIL (SMTP) ===
    # Se usa para enviar correos de contacto y notificaciones
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SENDER: str = os.getenv("SENDER", "notificaciones@profarmed.com.mx")
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "contacto@profarmed.com.mx")
    
    # === CONFIGURACION DE AWS (S3) ===
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID") or None
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY") or None
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    BUCKET_DOCS: str = os.getenv("BUCKET_DOCS", "")
    BUCKET_IMGS: str = os.getenv("BUCKET_IMGS", "")
    BUCKET_PROMOS: str = os.getenv("BUCKET_PROMOS", "")
    CLOUDFRONT_PROMOS_URL: str = os.getenv("CLOUDFRONT_PROMOS_URL", "")
    CLOUDFRONT_IMGS_URL: str = os.getenv("CLOUDFRONT_IMGS_URL", "")
    
    class Config:
        case_sensitive = True

# Instancia global de CONFIGURACION
settings = Settings()

# === VARIABLES DE COMPATIBILIDAD ===
# Mantener estas variables para codigo legacy que las use directamente
DATABASE_URL = settings.DATABASE_URL
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
SYNC_TOKEN_EXPIRE_MINUTES = settings.SYNC_TOKEN_EXPIRE_MINUTES
PROJECT_NAME = settings.PROJECT_NAME
API_V1_STR = settings.API_V1_STR
FRONTEND_URL = settings.FRONTEND_URL
TURNSTILE_SECRET_KEY = settings.TURNSTILE_SECRET_KEY