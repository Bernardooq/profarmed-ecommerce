import sys
from dbfread import DBF
import pandas as pd
from pathlib import Path

def leer_y_traducir_dbf(dbf_path, encoding="latin-1"):
    dbf_path = Path(dbf_path)
    
    # Buscar el archivo memo (.fpt) de forma insensible a mayúsculas/minúsculas
    fpt_path = None
    for ext in [".fpt", ".FPT", ".Fpt"]:
        p = dbf_path.with_suffix(ext)
        if p.exists():
            fpt_path = p
            break

    try:
        if fpt_path:
            print(f"Leyendo {dbf_path.name} con {fpt_path.name} (memo habilitado)")
            table = DBF(dbf_path, load=True, encoding=encoding)
        else:
            print(f"Leyendo {dbf_path.name} (sin memo)")
            table = DBF(dbf_path, load=True, ignore_missing_memofile=True, encoding=encoding)

        df = pd.DataFrame(iter(table))
        
        # Guardar en formato CSV en la misma carpeta
        csv_path = dbf_path.with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        print(f"Éxito: Guardado {csv_path.name} ({len(df)} filas, {len(df.columns)} columnas).")
        return df

    except Exception as e:
        print(f"Error leyendo/guardando {dbf_path.name}: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Si se pasa un argumento, se usa como carpeta, de lo contrario se usa backend/dbfs
    if len(sys.argv) > 1:
        carpeta = Path(sys.argv[1])
    else:
        carpeta = Path(__file__).resolve().parent.parent / "dbfs"

    print(f"Buscando archivos DBF en: {carpeta.resolve()}")

    if not carpeta.exists():
        print(f"Error: La carpeta {carpeta} no existe.")
        sys.exit(1)

    archivos = [f for f in carpeta.iterdir() if f.is_file() and f.suffix.lower() == ".dbf"]
    
    print(f"Se encontraron {len(archivos)} archivos DBF para procesar.")

    for i, archivo in enumerate(archivos, 1):
        print("=" * 80)
        print(f"[{i}/{len(archivos)}] Procesando: {archivo.name}")
        df = leer_y_traducir_dbf(archivo)
