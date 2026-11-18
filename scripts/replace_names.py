import os
import re

# ==========================================
# CONFIGURACIÓN DEL SCRIPT DE REEMPLAZO
# ==========================================
# Configura aquí las variables que quieres buscar y reemplazar para tu próximo proyecto.

# 1. Directorio raíz donde comenzará la búsqueda
# (Por defecto usa el directorio donde se encuentra este script)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Configuración de Nombres (Reemplazos exactos respetando mayúsculas)
# Asegúrate de escribir el valor "viejo" y el "nuevo" correspondiente.
OLD_NAME_LOWER = 'orozq'
NEW_NAME_LOWER = 'profarmed'

OLD_NAME_CAPITALIZED = 'Orozq'
NEW_NAME_CAPITALIZED = 'Profarmed'

OLD_NAME_UPPER = 'OROZQ'
NEW_NAME_UPPER = 'PROFARMED'

# (Opcional) Si existe otra variante exacta que necesites
OLD_NAME_PASCAL = 'Orozq'
NEW_NAME_PASCAL = 'Profarmed'

# 3. Configuración de Dominios (Reemplazo ignorando mayúsculas)
OLD_DOMAIN = r'orozq\.com'  # Importante: escapar los puntos con \ si es un regex
NEW_DOMAIN = 'profarmed.com.mx'

# 4. Exclusiones (Archivos y carpetas que el script NO debe tocar)
IGNORE_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist', '.idea', '.vscode'}
IGNORE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg', '.webp', '.pdf', '.zip', '.tar', '.gz', '.dbf', '.pyc'}

# IMPORTANTE: Ignoramos este propio script para que no modifique su propio código fuente.
SCRIPT_NAME = os.path.basename(__file__)

# ==========================================
# LÓGICA DEL SCRIPT (No necesitas tocar esto)
# ==========================================

def main():
    print(f"Iniciando reemplazo masivo en: {ROOT_DIR}")
    
    # Pre-compilamos el regex del dominio (case-insensitive)
    domain_re = re.compile(OLD_DOMAIN, re.IGNORECASE)
    files_modified = 0
    
    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        # Modificar dirnames in-place para no entrar en carpetas ignoradas
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        
        for filename in filenames:
            # Si es este script, nos lo saltamos
            if filename == SCRIPT_NAME:
                continue
                
            ext = os.path.splitext(filename)[1].lower()
            if ext in IGNORE_EXTS:
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            try:
                # Intentamos leer el archivo como texto UTF-8
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Probablemente sea un archivo binario o de otra codificación rara, lo saltamos
                continue
            except Exception as e:
                print(f"Error al leer {filepath}: {e}")
                continue
                
            original_content = content
            
            # 1. Reemplazar dominios primero
            content = domain_re.sub(NEW_DOMAIN, content)
            
            # 2. Reemplazar coincidencias exactas en orden específico
            content = content.replace(OLD_NAME_UPPER, NEW_NAME_UPPER)
            content = content.replace(OLD_NAME_PASCAL, NEW_NAME_PASCAL)
            content = content.replace(OLD_NAME_CAPITALIZED, NEW_NAME_CAPITALIZED)
            content = content.replace(OLD_NAME_LOWER, NEW_NAME_LOWER)
            
            # 3. Si hubo cambios, sobrescribir el archivo original
            if content != original_content:
                try:
                    with open(filepath, 'w', encoding='utf-8', newline='') as f:
                        f.write(content)
                    print(f"Modificado: {filepath}")
                    files_modified += 1
                except Exception as e:
                    print(f"Error al escribir {filepath}: {e}")
                    
    print(f"\n[OK] Proceso completado. Archivos modificados en total: {files_modified}")

if __name__ == "__main__":
    main()
