from fastapi import FastAPI, Request, Depends
from fastapi.responses import PlainTextResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from core import config
from db.session import engine
from dependencies import get_db
from routes.router import api_router
from routes.catalog import build_public_sitemap_xml
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title=config.PROJECT_NAME)

# Configurar CORS para permitir múltiples orígenes
allowed_origins = []
frontend_url = os.getenv("FRONTEND_URL", "*")

if frontend_url == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in frontend_url.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https://.*\.cloudfront\.net$|^https?://localhost(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error en {request.method} {request.url.path}: {exc}", exc_info=True)
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno del servidor: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": origin if origin != "null" else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )
app.include_router(api_router, prefix=config.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    return (
        "User-agent: *\n"
        "Allow: /sitemap.xml\n"
        "Allow: /api/v1/catalog/public/sitemap.xml\n"
        "Disallow: /\n"
    )


@app.get("/sitemap.xml")
def dynamic_sitemap_xml(db: Session = Depends(get_db)):
    """Sitemap XML dinámico del catálogo público storefront."""
    xml_content = build_public_sitemap_xml(db=db, default_domain="https://profarmed.com.mx")
    return Response(
        content=xml_content,
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )

@app.get("/")
def read_root():
    try:
        with engine.connect() as connection:
            return {"message": "OK"}
    except Exception as e:
        logger.error(f"DB connection error: {e}", exc_info=True)
        return {"message": "OK"}