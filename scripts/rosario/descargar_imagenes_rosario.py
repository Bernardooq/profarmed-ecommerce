#!/usr/bin/env python3
"""
Script de Descarga Masiva de Imágenes - ExpoMR / e-Indigo
=========================================================
- Lee los productos desde Rosario.xlsx (3,990+ productos).
- Autentica automáticamente en https://e-indigo.com/ vía Playwright Headless.
- Transfiere la sesión a un cliente HTTP de alta velocidad.
- Para cada producto, crea una subcarpeta con su Código de Barras dentro de `imagenes/`.
- Descarga todas las imágenes (portada y ángulos/detalles) asignándoles nombres secuenciales (1.jpg, 2.jpg, ...).
- Es 100% reanudable (si se interrumpe, omite los productos ya descargados).
"""

import os
import sys
import time
import re
import html
import openpyxl
import requests
import asyncio
from playwright.async_api import async_playwright

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rosario.xlsx")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagenes")

LOGIN_URL = "https://e-indigo.com/Default.aspx"
PRODUCT_URL_TEMPLATE = "https://e-indigo.com/App/Producto.aspx?Id={sku}"
BASE_APP_URL = "https://e-indigo.com/App/"

USERNAME = "hector_soltero@hotmail.com"
PASSWORD = "dmi1236"


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def CargarProductosExcel(filepath):
    """
    Lee Rosario.xlsx y retorna una lista de diccionarios con SKU, Código de Barras y Producto.
    """
    if not os.path.exists(filepath):
        print(f"🚨 Error: No se encontró el archivo Excel en {filepath}")
        sys.exit(1)

    print(f"📖 Leyendo datos de {filepath}...")
    wb = openpyxl.load_workbook(filepath, data_only=True)
    sheet = wb.active

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        print("🚨 Error: El archivo Excel está vacío.")
        sys.exit(1)

    header = [str(cell).strip() if cell else "" for cell in rows[0]]
    
    # Encontrar índices de columnas SKU, Codigo y Producto
    sku_idx = header.index("SKU") if "SKU" in header else 0
    codigo_idx = header.index("Codigo") if "Codigo" in header else 1
    prod_idx = header.index("Producto") if "Producto" in header else 2

    productos = []
    for r in rows[1:]:
        if not r or r[sku_idx] is None:
            continue
        
        sku = str(r[sku_idx]).strip()
        codigo = str(r[codigo_idx]).strip() if r[codigo_idx] else f"SKU_{sku}"
        nombre = str(r[prod_idx]).strip() if r[prod_idx] else "Sin Nombre"
        
        # Limpiar posibles notaciones científicas o floats en códigos
        if codigo.endswith(".0"):
            codigo = codigo[:-2]
            
        productos.append({
            "sku": sku,
            "codigo": codigo,
            "nombre": nombre
        })

    print(f"✅ Se cargaron {len(productos)} productos desde el Excel.")
    return productos


async def AutenticarPlaywright():
    """
    Realiza login headless con Playwright y devuelve una sesión de requests con las cookies de auth.
    """
    print("🔑 Autenticando en e-indigo.com vía Playwright (Headless)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(LOGIN_URL, wait_until="networkidle")
        await page.fill("#logLogin_UserName", USERNAME)
        await page.fill("#logLogin_Password", PASSWORD)

        async with page.expect_navigation(wait_until="networkidle"):
            await page.click("#logLogin_LoginButton")

        print("✅ Autenticado con éxito en e-indigo!")

        cookies = await context.cookies()
        await browser.close()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])

    return session


def ObtenerUrlsImagenesProducto(session, sku):
    """
    Obtiene todas las URLs únicas de las imágenes de un producto dada su SKU.
    """
    url = PRODUCT_URL_TEMPLATE.format(sku=sku)
    try:
        res = session.get(url, timeout=10)
        if res.status_code != 200:
            return []

        # Buscar todos los src con ihFoto.ashx
        raw_matches = re.findall(r'src=[\"\'](ihFoto\.ashx[^\'\"]+)[\"\']', res.text, re.IGNORECASE)
        
        urls = []
        # Agregar portada principal explícitamente primero si no apareció
        portada_url = f"{BASE_APP_URL}ihFoto.ashx?Id={sku}"
        urls.append(portada_url)

        for match in raw_matches:
            clean_rel = html.unescape(match)
            full_url = f"{BASE_APP_URL}{clean_rel}"
            if full_url not in urls:
                urls.append(full_url)

        return urls
    except Exception as e:
        print(f"   ⚠️ Error al consultar producto SKU {sku}: {e}")
        return []


def DescargarImagen(session, url, dest_path):
    """
    Descarga una imagen de forma segura y valida que sea una imagen real (> 1KB).
    """
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 1024:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
        return False
    except Exception:
        return False


# ============================================================================
# PROCESO PRINCIPAL DE DESCARGA
# ============================================================================

def main():
    print("======================================================================")
    print("   DESCARGADOR MASIVO DE IMÁGENES POR CÓDIGO DE BARRAS (EXPOMR)       ")
    print("======================================================================")

    # 1. Cargar productos de Excel
    productos = CargarProductosExcel(EXCEL_PATH)

    # 2. Autenticar y crear sesión HTTP
    session = asyncio.run(AutenticarPlaywright())

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total = len(productos)
    procesados = 0
    descargados = 0
    omitidos = 0
    errores = 0
    total_imgs_descargadas = 0

    t_inicio = time.time()

    print(f"\n📁 Guardando imágenes en la carpeta: {OUTPUT_DIR}\n")

    for idx, prod in enumerate(productos, 1):
        sku = prod["sku"]
        codigo = prod["codigo"]
        nombre = prod["nombre"]

        # Limpiar caracteres ilegales en Windows (\ / : * ? " < > |) para nombres de carpeta
        codigo_limpio = re.sub(r'[\/*?:"<>|]', '', str(codigo)).strip() or f"sku_{sku}"

        # Carpeta destino para este código de barras
        folder_prod = os.path.join(OUTPUT_DIR, codigo_limpio)

        # Si la carpeta ya existe y tiene archivos .jpg -> Omitir (Reanudable)
        if os.path.exists(folder_prod) and any(f.endswith(".jpg") for f in os.listdir(folder_prod)):
            imgs_existentes = len([f for f in os.listdir(folder_prod) if f.endswith(".jpg")])
            print(f"[{idx}/{total}] ⏩ OMITIDO (Ya descargado): Código {codigo_limpio} | {imgs_existentes} imágenes")
            omitidos += 1
            continue

        # Obtener URLs de imágenes
        img_urls = ObtenerUrlsImagenesProducto(session, sku)

        if not img_urls:
            print(f"[{idx}/{total}] ⚠️ Sin imágenes: Código {codigo} (SKU {sku})")
            errores += 1
            continue

        # Crear carpeta para el producto
        os.makedirs(folder_prod, exist_ok=True)

        count_descargadas = 0
        img_num = 1

        for url in img_urls:
            dest_file = os.path.join(folder_prod, f"{img_num}.jpg")
            exito = DescargarImagen(session, url, dest_file)
            if exito:
                count_descargadas += 1
                img_num += 1

        if count_descargadas > 0:
            print(f"[{idx}/{total}] ✅ Guardado: Código {codigo} (SKU {sku}) ➔ {count_descargadas} imágenes")
            descargados += 1
            total_imgs_descargadas += count_descargadas
        else:
            # Si no se pudo guardar ninguna, borrar la carpeta vacía
            if os.path.exists(folder_prod) and not os.listdir(folder_prod):
                os.rmdir(folder_prod)
            print(f"[{idx}/{total}] ❌ Falló la descarga: Código {codigo} (SKU {sku})")
            errores += 1

        procesados += 1

        # Breve pausa para no saturar el servidor (0.05 segundos)
        time.sleep(0.05)

    t_total = time.time() - t_inicio

    print("\n======================================================================")
    print("                      RESUMEN DE DESCARGA                              ")
    print("======================================================================")
    print(f"⏱️ Tiempo Total:            {t_total / 60:.2f} minutos")
    print(f"📦 Productos Procesados:     {total}")
    print(f"✅ Productos Descargados:    {descargados}")
    print(f"⏩ Productos Omitidos (Prev):{omitidos}")
    print(f"⚠️ Errores / Sin imagen:    {errores}")
    print(f"🖼️ Total Fotos Guardadas:   {total_imgs_descargadas} imágenes en {OUTPUT_DIR}")
    print("======================================================================\n")


if __name__ == "__main__":
    main()
