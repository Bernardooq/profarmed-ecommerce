#!/usr/bin/env python3
"""
Compresor adaptativo de imágenes a WebP (<50KB objetivo).
Modo local sin notificación al backend.
"""

import os
import requests
from PIL import Image

from ..config import IMAGES_FOLDER, IMAGES_FOLDER_INPUT, BACKEND_URL
from ..uploader.api_client import login

SOURCE_FOLDER = IMAGES_FOLDER_INPUT
OUTPUT_FOLDER = IMAGES_FOLDER

WEBP_QUALITY = 70
MAX_DIMENSION = 1200
TARGET_SIZE_KB = 50
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"}
NOTIFY_IMAGE_VERSION = False


def create_output_folder():
    """Crea la carpeta destino si no existe."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Carpeta destino: {OUTPUT_FOLDER}")


def get_size_mb(path) -> float:
    return os.path.getsize(path) / (1024 * 1024)


def get_size_kb(path) -> float:
    return os.path.getsize(path) / 1024


def notify_image_version(product_id: str, token: str | None):
    """Notifica al backend que la imagen del producto cambió."""
    if not NOTIFY_IMAGE_VERSION or not token:
        return
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.patch(
            f"{BACKEND_URL}/products/{product_id}/image-version",
            headers=headers,
            timeout=15,
        )
        if response.status_code == 200:
            print(f" [API] Versión de imagen actualizada para {product_id}")
        elif response.status_code != 404:
            print(f" [API] Error {response.status_code} al actualizar {product_id}")
    except Exception as exc:
        print(f" [API] Error de red: {exc}")


def compress_image_to_webp(image_path, token=None):
    """Convierte imagen a WebP adaptativo intentando quedar debajo de TARGET_SIZE_KB."""
    try:
        base_name = image_path.stem
        webp_path = OUTPUT_FOLDER / f"{base_name}.webp"

        if webp_path.exists():
            if webp_path.stat().st_mtime >= image_path.stat().st_mtime:
                return False, 0, 0
            print(f"[UPDATE] Actualizando: {base_name}.webp (el original es más reciente)")

        with Image.open(image_path) as img:
            original_mb = get_size_mb(image_path)

            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            current_dim = MAX_DIMENSION
            current_quality = WEBP_QUALITY
            attempt = 0
            max_attempts = 6

            while attempt < max_attempts:
                processed = img.copy()
                resized = False

                if max(processed.size) > current_dim:
                    if processed.width > processed.height:
                        new_w = current_dim
                        new_h = int((current_dim / processed.width) * processed.height)
                    else:
                        new_h = current_dim
                        new_w = int((current_dim / processed.height) * processed.width)
                    processed = processed.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    resized = True

                processed.save(webp_path, "WEBP", quality=current_quality, method=6)
                final_kb = get_size_kb(webp_path)

                if final_kb <= TARGET_SIZE_KB:
                    final_mb = get_size_mb(webp_path)
                    reduction = ((original_mb - final_mb) / original_mb) * 100
                    if original_mb >= 0.1:
                        print(f"[OK] {base_name}: {original_mb:.2f}MB -> {final_kb:.1f}KB ({reduction:.0f}%)", end="")
                    else:
                        orig_kb = get_size_kb(image_path)
                        print(f"[OK] {base_name}: {orig_kb:.1f}KB -> {final_kb:.1f}KB ({reduction:.0f}%)", end="")

                    if resized or attempt > 0:
                        extras = []
                        if resized:
                            extras.append(f"{processed.width}x{processed.height}")
                        if attempt > 0:
                            extras.append(f"q:{current_quality}")
                        print(f" [{', '.join(extras)}]")
                    else:
                        print()

                    notify_image_version(base_name, token)
                    return True, original_mb, final_mb

                attempt += 1
                if attempt <= 2:
                    current_quality = max(45, current_quality - 12)
                else:
                    current_dim = int(current_dim * 0.80)
                    current_quality = max(45, current_quality - 8)

            final_mb = get_size_mb(webp_path)
            final_kb = get_size_kb(webp_path)
            reduction = ((original_mb - final_mb) / original_mb) * 100
            print(f"[!] {base_name}: {original_mb:.2f}MB -> {final_kb:.1f}KB ({reduction:.0f}%) [excede {TARGET_SIZE_KB}KB]")
            notify_image_version(base_name, token)
            return True, original_mb, final_mb

    except Exception as exc:
        print(f"[ERR] Error con {image_path.name}: {exc}")
        return False, 0, 0


def main():
    print("=" * 70)
    print("Compresor ADAPTATIVO de Imágenes a WebP")
    print(f"  Objetivo: <{TARGET_SIZE_KB}KB por imagen")
    print("=" * 70)
    print()

    if not SOURCE_FOLDER.exists():
        print(f"[ERROR] No existe la carpeta {SOURCE_FOLDER}")
        return

    create_output_folder()
    print()

    token = None
    if NOTIFY_IMAGE_VERSION:
        print("[INFO] Autenticando con el backend...")
        token = login()
        if not token:
            print("[WARN] No se pudo conectar al backend. El control de versiones de imagen no funcionará.")
        else:
            print("[OK] Autenticado correctamente")
        print()

    images = []
    for ext in SUPPORTED_FORMATS:
        images.extend(SOURCE_FOLDER.glob(f"*{ext}"))
        images.extend(SOURCE_FOLDER.glob(f"*{ext.upper()}"))

    if not images:
        print(f"[!] No se encontraron imágenes en {SOURCE_FOLDER}")
        return

    print(f"[INFO] Encontradas {len(images)} imágenes\n")

    success_count = 0
    total_original_mb = 0.0
    total_final_mb = 0.0
    under_target = 0

    for image_path in sorted(images):
        ok, orig, final = compress_image_to_webp(image_path, token=token)
        if ok:
            success_count += 1
            total_original_mb += orig
            total_final_mb += final
            webp_path = OUTPUT_FOLDER / f"{image_path.stem}.webp"
            if webp_path.exists() and get_size_kb(webp_path) <= TARGET_SIZE_KB:
                under_target += 1

    print()
    print("=" * 70)
    print("[OK] Compresión completada")
    print(f"  Procesadas: {success_count}/{len(images)} imágenes")
    if success_count > 0:
        print(f"  Bajo objetivo (<{TARGET_SIZE_KB}KB): {under_target}/{success_count} ({under_target * 100 / success_count:.0f}%)")
        print(f"  Tamaño original total: {total_original_mb:.2f} MB")
        print(f"  Tamaño final total: {total_final_mb:.2f} MB")
        total_reduction = ((total_original_mb - total_final_mb) / total_original_mb) * 100
        print(f"  Reducción total: {total_reduction:.1f}%")
        print(f"  Ahorro: {total_original_mb - total_final_mb:.2f} MB")
    print("=" * 70)


if __name__ == "__main__":
    main()
