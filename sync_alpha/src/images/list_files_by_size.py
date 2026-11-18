#!/usr/bin/env python3
"""
Analizador de tamaño de archivos en el directorio de imágenes origen.
"""

from ..config import IMAGES_FOLDER_INPUT

FOLDER_TO_ANALYZE = IMAGES_FOLDER_INPUT
FILE_EXTENSIONS = {".webp", ".jpg", ".jpeg"}


def format_size(bytes_size: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def get_files_with_size(folder, extensions=None):
    files = []
    for file_path in folder.rglob("*"):
        if not file_path.is_file():
            continue
        if extensions and file_path.suffix.lower() not in extensions:
            continue
        try:
            files.append((file_path, file_path.stat().st_size, file_path.name))
        except OSError:
            continue
    files.sort(key=lambda x: x[1], reverse=True)
    return files


def main():
    print("=" * 80)
    print("Analizador de Tamaño de Archivos")
    print("=" * 80)
    print()

    if not FOLDER_TO_ANALYZE.exists():
        print(f"[ERROR] No existe la carpeta {FOLDER_TO_ANALYZE}")
        return

    print(f"Carpeta: {FOLDER_TO_ANALYZE}")
    print(f"Filtro: {', '.join(sorted(FILE_EXTENSIONS)) if FILE_EXTENSIONS else 'Todos los archivos'}\n")

    files = get_files_with_size(FOLDER_TO_ANALYZE, FILE_EXTENSIONS)
    if not files:
        print("[!] No se encontraron archivos")
        return

    total_size = sum(size for _, size, _ in files)
    print("=" * 80)
    print(f"{'NOMBRE':<50} {'TAMAÑO':>15} {'% DEL TOTAL':>10}")
    print("=" * 80)

    for _, size, name in files:
        pct = (size / total_size) * 100 if total_size > 0 else 0.0
        display_name = name if len(name) <= 48 else name[:45] + "..."
        print(f"{display_name:<50} {format_size(size):>15} {pct:>9.1f}%")

    print("=" * 80)
    print(f"Total de archivos: {len(files)}")
    print(f"Tamaño total: {format_size(total_size)}")
    if files:
        print(f"Tamaño promedio: {format_size(total_size / len(files))}")
        print(f"Más grande: {files[0][2]} ({format_size(files[0][1])})")
        print(f"Más pequeño: {files[-1][2]} ({format_size(files[-1][1])})")
    print("=" * 80)


if __name__ == "__main__":
    main()
