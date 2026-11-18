"""
Compresor de Imágenes a WebP - Compresión Adaptativa para Profarmed
Convierte imágenes JPG/PNG a WebP con compresión adaptativa a <50KB.
"""

from pathlib import Path
from PIL import Image
import os
import sys

# Permitir importación desde src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import IMAGES_FOLDER_INPUT, IMAGES_FOLDER_OUTPUT

SOURCE_FOLDER = IMAGES_FOLDER_INPUT
OUTPUT_FOLDER = IMAGES_FOLDER_OUTPUT
WEBP_QUALITY = 70
MAX_DIMENSION = 1200
TARGET_SIZE_KB = 50
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'}


def compress_image_to_webp(input_path: Path, output_path: Path) -> tuple:
    """Comprime una imagen individual adaptativamente a WebP."""
    try:
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            orig_width, orig_height = img.size
            if max(orig_width, orig_height) > MAX_DIMENSION:
                scale = MAX_DIMENSION / max(orig_width, orig_height)
                new_size = (int(orig_width * scale), int(orig_height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
            output_path.parent.mkdir(parents=True, exist_ok=True)
            quality = WEBP_QUALITY
            img.save(output_path, 'WEBP', quality=quality, method=4)
            
            # Ajuste adaptativo si supera TARGET_SIZE_KB
            attempts = 0
            while output_path.stat().st_size > (TARGET_SIZE_KB * 1024) and quality > 30 and attempts < 3:
                quality -= 15
                img.save(output_path, 'WEBP', quality=quality, method=6)
                attempts += 1
                
            final_size = output_path.stat().st_size
            orig_size = input_path.stat().st_size
            return True, orig_size, final_size
    except Exception as e:
        return False, 0, str(e)


def run_compression():
    print(f"Buscando imágenes en: {SOURCE_FOLDER}")
    print(f"Destino WebP: {OUTPUT_FOLDER}")
    
    if not SOURCE_FOLDER.exists():
        print(f"[!] La carpeta de origen {SOURCE_FOLDER} no existe.")
        return
        
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    # Recorrido recursivo para soportar subcarpetas por código de barras: <INPUT>/<codebar>/1.jpg
    files = sorted(
        f for f in SOURCE_FOLDER.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    )
    print(f"Total imágenes encontradas: {len(files)}")

    success_count = 0
    skipped_count = 0
    for f in files:
        rel_path = f.relative_to(SOURCE_FOLDER)
        out_f = OUTPUT_FOLDER / rel_path.parent / f"{rel_path.stem}.webp"

        # Omitir si el .webp ya existe y es más reciente o igual que el archivo origen
        if out_f.exists() and out_f.stat().st_mtime >= f.stat().st_mtime:
            skipped_count += 1
            continue

        ok, _, _ = compress_image_to_webp(f, out_f)
        if ok:
            success_count += 1

    print(f"Procesadas {success_count}/{len(files)} imágenes a WebP ({skipped_count} ya optimizadas/omitidas).")


if __name__ == "__main__":
    run_compression()

