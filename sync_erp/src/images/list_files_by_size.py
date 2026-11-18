"""
Utilidad para listar imágenes ordenadas por tamaño.
"""

from pathlib import Path
import sys

# Permitir importación desde src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import IMAGES_FOLDER_INPUT, IMAGES_FOLDER_OUTPUT


def list_files(folder_path: Path, limit=20):
    if not folder_path.exists():
        print(f"Carpeta {folder_path} no existe.")
        return
        
    files = [(f, f.stat().st_size) for f in folder_path.rglob("*") if f.is_file()]
    files.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nTop {limit} archivos más pesados en {folder_path}:")
    for f, size in files[:limit]:
        rel = f.relative_to(folder_path)
        print(f"  {size/1024:.1f} KB - {rel}")


if __name__ == "__main__":
    list_files(IMAGES_FOLDER_OUTPUT)

