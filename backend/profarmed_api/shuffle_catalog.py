"""
Script de Barajado / Rotación Periódica de Catálogo
Ejecutable por cronjob semanal.

Verifica si la bandera 'catalog.weekly_rotation' está activa en system_configs.
Si está activa, baraja solo los productos con display_priority >= 1,000,000.
"""

import sys
import os

# Asegurar que el path del backend esté disponible
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import SessionLocal
from db.base import SystemConfig
from crud.crud_product import shuffle_catalog_priorities


def main():
    db = SessionLocal()
    try:
        # 1. Verificar si la rotación semanal está habilitada
        cfg = db.query(SystemConfig).filter(
            (SystemConfig.config_id == 104) | (SystemConfig.config_name == "catalog.weekly_rotation")
        ).first()

        if not cfg or not cfg.is_active:
            print("[SHUFFLE] La rotación semanal (catalog.weekly_rotation) está DESACTIVADA. Omitiendo.")
            return

        # 2. Ejecutar el barajado
        count = shuffle_catalog_priorities(db)
        print(f"[SHUFFLE] Éxito: {count} productos rotados en el catálogo.")
    except Exception as e:
        print(f"[SHUFFLE ERROR] Falló la rotación semanal del catálogo: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
