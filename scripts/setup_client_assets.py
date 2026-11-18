"""
=============================================================================
HERRAMIENTA INTEGRAL DE BRANDING & ASSETS PARA NUEVOS CLIENTES / TENANTS
=============================================================================
Este script automatiza el reemplazo, optimización y compresión de:
1. Favicon y Conjunto PWA Icons (72x72, 96x96, 128x128, 144x144, 152x152, 192x192, 384x384, 512x512)
2. Imágenes Principales de la Landing Page (inicio, login, nosotros, footer-logo)
3. Productos Destacados de Landing (p1, p2, p3, p4) en WebP y PNG
4. Logos de Laboratorios / Fabricantes (lab1..labN)

Requisitos:
- Python 3.8+ con Pillow instalado (`pip install Pillow`)
=============================================================================
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

try:
    from PIL import Image
except ImportError:
    print("\n[ERROR] Se requiere la librería Pillow para procesar imágenes.")
    print("Por favor instala Pillow ejecutando: pip install Pillow\n")
    sys.exit(1)

# Rutas base relativas
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REACT_DIR = REPO_ROOT / "react"
PUBLIC_DIR = REACT_DIR / "public"
PWA_ICONS_DIR = PUBLIC_DIR / "pwa-icons"
IMAGES_DIR = REACT_DIR / "src" / "images"
LABS_DIR = IMAGES_DIR / "labs"
PRODS_DIR = IMAGES_DIR / "prods"

PWA_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def prompt_path(message: str, must_exist: bool = True, allow_skip: bool = True) -> Optional[Path]:
    """Solicita una ruta al usuario. Permite presionar Enter o 's' para saltar/skipear sin error."""
    skip_msg = " [Enter o 's' para saltar, 'c' para cancelar]" if allow_skip else " ['c' para cancelar]"
    while True:
        raw = input(f"{message}{skip_msg}: ").strip()
        if not raw or raw.lower() == 's':
            if allow_skip:
                print("  [-] Paso omitido / conservando actual.")
                return None
            else:
                continue
        if raw.lower() == 'c':
            return None
        # Limpiar comillas si se arrastra archivo a la consola de Windows
        clean = raw.strip('"').strip("'")
        p = Path(clean).resolve()
        if must_exist and not p.exists():
            print(f"[!] La ruta especificada no existe: {p}")
            continue
        return p


def process_pwa_and_favicon():
    """Genera favicon.webp y todos los iconos PWA a partir de un logo maestro."""
    print_header("1. Generador de Favicon & PWA Icons")
    print("Selecciona tu imagen/logo fuente (PNG o WebP en alta resolución, preferiblemente cuadrado):")
    
    src_path = prompt_path("Ruta del logo maestro")
    if not src_path:
        print("[*] Operación cancelada.")
        return

    try:
        img = Image.open(src_path).convert("RGBA")
    except Exception as e:
        print(f"[ERROR] No se pudo abrir la imagen: {e}")
        return

    # 1. Limpiar y recrear directorio de iconos PWA
    PWA_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in PWA_ICONS_DIR.glob("*.png"):
        old_file.unlink()
    print("[✓] Carpeta public/pwa-icons/ limpiada.")

    # 2. Generar iconos PWA en formato PNG transparente de alta compresión
    for size in PWA_SIZES:
        out_path = PWA_ICONS_DIR / f"icon-{size}x{size}.png"
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(out_path, format="PNG", optimize=True)
        print(f"  [+] Generado: public/pwa-icons/icon-{size}x{size}.png ({size}x{size})")

    # 3. Generar favicon.webp (64x64 o 128x128 optimizado)
    fav_path = PUBLIC_DIR / "favicon.webp"
    fav_img = img.resize((128, 128), Image.Resampling.LANCZOS)
    fav_img.save(fav_path, format="WEBP", quality=90, method=6)
    print(f"  [+] Generado: public/favicon.webp (128x128 WebP)")

    print("\n[✓] ¡Favicon y PWA Icons generados y optimizados con éxito!\n")


def optimize_and_save_dual(img: Image.Image, base_path: Path, max_dimension: int = 1920, webp_quality: int = 85):
    """Guarda una imagen optimizada en formato .webp y .png."""
    # Redimensionar proporcionalmente si supera la dimensión máxima
    w, h = img.size
    if max(w, h) > max_dimension:
        if w >= h:
            new_w = max_dimension
            new_h = int(h * (max_dimension / w))
        else:
            new_h = max_dimension
            new_w = int(w * (max_dimension / h))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 1. Guardar WebP comprimido
    webp_path = base_path.with_suffix(".webp")
    if img.mode == "RGBA":
        img.save(webp_path, format="WEBP", quality=webp_quality, method=6)
    else:
        rgb_img = img.convert("RGB")
        rgb_img.save(webp_path, format="WEBP", quality=webp_quality, method=6)

    # 2. Guardar PNG optimizado
    png_path = base_path.with_suffix(".png")
    img.save(png_path, format="PNG", optimize=True)

    print(f"  [+] Guardado: {webp_path.name} ({os.path.getsize(webp_path) // 1024} KB) y {png_path.name}")


def process_landing_page_images():
    """Permite reemplazar imágenes clave de la landing (inicio, login, nosotros, footer-logo)."""
    print_header("2. Actualizar Imágenes de Landing Page")
    print("Opciones de imagen disponibles para actualizar:")
    print("  1. inicio      (Hero principal / Banner inicio)")
    print("  2. login       (Ilustración de fondo en modal/pantalla login)")
    print("  3. nosotros    (Imagen representativa institucional / about us)")
    print("  4. footer-logo (Logo para pie de página)")
    print("  5. Todas las anteriores en lote (carpeta)")

    opt = input("\nElige una opción (1-5 o 'c' para cancelar): ").strip()
    if opt == 'c':
        return

    mapping = {
        "1": "inicio",
        "2": "login",
        "3": "nosotros",
        "4": "footer-logo"
    }

    if opt in mapping:
        name = mapping[opt]
        src = prompt_path(f"Ruta de la nueva imagen para '{name}'")
        if not src:
            return
        img = Image.open(src).convert("RGBA")
        optimize_and_save_dual(img, IMAGES_DIR / name)
        print(f"\n[✓] Imagen '{name}' actualizada y comprimida exitosamente.\n")

    elif opt == "5":
        src_folder = prompt_path("Ruta de la carpeta contenedora con las imágenes nuevas", must_exist=True)
        if not src_folder or not src_folder.is_dir():
            print("[!] La ruta no es una carpeta válida.")
            return

        for name in ["inicio", "login", "nosotros", "footer-logo"]:
            # Buscar archivo coincidente sin importar extensión
            matched = list(src_folder.glob(f"{name}.*"))
            if matched:
                img = Image.open(matched[0]).convert("RGBA")
                optimize_and_save_dual(img, IMAGES_DIR / name)
            else:
                print(f"  [-] Omitido: No se encontró '{name}' en la carpeta.")
        print("\n[✓] Proceso en lote completado.\n")


def process_landing_products():
    """Actualiza los 4 productos destacados de la landing page (p1, p2, p3, p4)."""
    print_header("3. Actualizar Productos Destacados de Landing (p1..p4)")
    print("Esta opción actualiza las 4 fotos de medicamentos / productos de la landing page.")
    print("  1. Actualizar individualmente (p1, p2, p3 o p4)")
    print("  2. Actualizar los 4 desde una carpeta (deben llamarse p1, p2, p3, p4)")

    sub = input("\nElige (1-2 o 'c'): ").strip()
    if sub == '1':
        p_num = input("Ingresa el número de producto (1, 2, 3 o 4): ").strip()
        if p_num not in ["1", "2", "3", "4"]:
            print("[!] Opción inválida.")
            return
        src = prompt_path(f"Ruta de la imagen para p{p_num}")
        if not src:
            return
        img = Image.open(src).convert("RGBA")
        optimize_and_save_dual(img, IMAGES_DIR / f"p{p_num}", max_dimension=1200)
        optimize_and_save_dual(img, PRODS_DIR / f"p{p_num}", max_dimension=1200)
        print(f"[✓] Producto p{p_num} actualizado exitosamente.")

    elif sub == '2':
        src_folder = prompt_path("Ruta de la carpeta con imágenes (p1..p4)", must_exist=True)
        if not src_folder:
            return
        PRODS_DIR.mkdir(parents=True, exist_ok=True)
        for i in range(1, 5):
            name = f"p{i}"
            matched = list(src_folder.glob(f"{name}.*"))
            if matched:
                img = Image.open(matched[0]).convert("RGBA")
                optimize_and_save_dual(img, IMAGES_DIR / name, max_dimension=1200)
                optimize_and_save_dual(img, PRODS_DIR / name, max_dimension=1200)
            else:
                print(f"  [-] Omitido: {name} no encontrado en carpeta.")
        print("\n[✓] Productos p1..p4 actualizados y comprimidos con éxito.")


def process_laboratories_logos():
    """Reemplaza o actualiza el carrusel de laboratorios (lab1..labN.webp)."""
    print_header("4. Actualizar Logos de Laboratorios (lab1..labN)")
    print("Selecciona una carpeta con los logos de laboratorios (formato PNG/JPG/WebP).")
    print("El script los ordenará y generará en formato WebP transparente ultraligero.")

    folder = prompt_path("Ruta de la carpeta de logos de laboratorios", must_exist=True)
    if not folder:
        return

    LABS_DIR.mkdir(parents=True, exist_ok=True)

    # Preguntar si se limpian los anteriores
    clean_old = input("¿Deseas borrar los logos de laboratorios actuales antes de copiar los nuevos? (s/n): ").strip().lower()
    if clean_old == 's':
        for old in IMAGES_DIR.glob("lab*.webp"):
            old.unlink()
        for old in LABS_DIR.glob("lab*.webp"):
            old.unlink()
        print("[✓] Logos anteriores eliminados.")

    # Buscar todas las imágenes válidas
    extensions = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    found_files: List[Path] = []
    for ext in extensions:
        found_files.extend(folder.glob(ext))
    found_files.sort(key=lambda x: x.name)

    if not found_files:
        print("[!] No se encontraron imágenes en la carpeta especificada.")
        return

    print(f"\nProcesando {len(found_files)} logos de laboratorios...")
    for idx, fpath in enumerate(found_files, start=1):
        try:
            img = Image.open(fpath).convert("RGBA")
            # Redimensionar logo a un ancho máximo de 300px manteniendo proporción
            w, h = img.size
            if w > 300:
                new_w = 300
                new_h = int(h * (300 / w))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Guardar en images/ y en images/labs/
            out_name = f"lab{idx}.webp"
            img.save(IMAGES_DIR / out_name, format="WEBP", quality=85, method=6)
            img.save(LABS_DIR / out_name, format="WEBP", quality=85, method=6)
            print(f"  [+] Generado: {out_name} (desde {fpath.name})")
        except Exception as e:
            print(f"  [!] Error procesando {fpath.name}: {e}")

    print(f"\n[✓] ¡Se generaron {len(found_files)} logos en formato WebP con éxito!\n")


def full_branding_wizard():
    """Asistente integral paso a paso."""
    print_header("Asistente Completo de Branding & Assets")
    print("Este asistente te guiará para configurar un nuevo tenant de punta a punta.\n")
    
    print("PASO 1: Favicon & PWA Icons")
    process_pwa_and_favicon()
    
    print("\nPASO 2: Imágenes de Landing Page")
    process_landing_page_images()
    
    print("\nPASO 3: Productos Destacados de Landing")
    process_landing_products()
    
    print("\nPASO 4: Logos de Laboratorios")
    process_laboratories_logos()
    
    print_header("¡Proceso de Branding y Assets Completado!")
    print("Siguiente paso recomendado: npm run build en la carpeta react/\n")


def main():
    while True:
        print_header("Generador & Optimizador de Assets / Branding (PROFARMED Suite)")
        print("  1. 🎨 Generar Favicon & Conjunto PWA Icons (72..512px)")
        print("  2. 🖼️  Actualizar Imágenes de Landing (inicio, login, nosotros, footer-logo)")
        print("  3. 💊 Actualizar Productos Destacados de Landing (p1..p4)")
        print("  4. 🧪 Actualizar Logos de Laboratorios (lab1..labN.webp)")
        print("  5. 🚀 ASISTENTE COMPLETO (Paso a paso para nuevo cliente)")
        print("  0. Salir")
        
        choice = input("\nSelecciona una opción (0-5): ").strip()
        
        if choice == "1":
            process_pwa_and_favicon()
        elif choice == "2":
            process_landing_page_images()
        elif choice == "3":
            process_landing_products()
        elif choice == "4":
            process_laboratories_logos()
        elif choice == "5":
            full_branding_wizard()
        elif choice == "0":
            print("\n¡Hasta luego!\n")
            break
        else:
            print("[!] Opción no válida. Intenta de nuevo.")


if __name__ == "__main__":
    main()
