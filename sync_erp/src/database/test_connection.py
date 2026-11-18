"""
Script de diagnóstico para probar la conexión a SQL Server 2000.
Ejecución: python src/database/test_connection.py
"""

import sys
from pathlib import Path

# Permitir importación desde src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import (
    ERP_DB_DRIVER, ERP_DB_HOST, ERP_DB_PORT,
    ERP_DB_NAME, ERP_DB_USER, ERP_DB_PASSWORD
)


def test_connection():
    print("=" * 60)
    print("PROBANDO CONEXIÓN A SQL SERVER 2000")
    print("=" * 60)
    print(f"Driver configurado : {{{ERP_DB_DRIVER}}}")
    print(f"Servidor / Host    : {ERP_DB_HOST}:{ERP_DB_PORT}")
    print(f"Base de datos      : {ERP_DB_NAME}")
    print(f"Usuario            : {ERP_DB_USER}")
    print("-" * 60)
    
    try:
        import pyodbc
    except ImportError:
        print("[ERROR] pyodbc no está instalado. Ejecuta: pip install pyodbc")
        return False
        
    drivers_disponibles = pyodbc.drivers()
    print(f"Drivers ODBC detectados en Windows: {drivers_disponibles}")
    print("-" * 60)
    
    # Intentar con el driver configurado o con los drivers compatibles con SQL Server 2000
    candidatos_drivers = [
        ERP_DB_DRIVER,
        "SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server Native Client 10.0"
    ]
    
    # Eliminar duplicados preservando orden
    candidatos = []
    for d in candidatos_drivers:
        if d in drivers_disponibles and d not in candidatos:
            candidatos.append(d)
            
    if not candidatos:
        print("[ERROR] No se encontró ningún driver compatible con SQL Server instalado.")
        return False
        
    for driver in candidatos:
        print(f"\n-> Probando con DRIVER={{{driver}}}...")
        
        # Conexión con puerto
        server_str = f"{ERP_DB_HOST},{ERP_DB_PORT}" if ERP_DB_PORT and str(ERP_DB_PORT) != "1433" else ERP_DB_HOST
        
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server_str};"
            f"DATABASE={ERP_DB_NAME};"
            f"UID={ERP_DB_USER};"
            f"PWD={ERP_DB_PASSWORD};"
        )
        
        try:
            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()
            
            # Obtener versión de SQL Server
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            print("\n  [EXITO] ¡Conexión establecida con éxito!")
            print(f"  Versión del Motor:\n  {version.strip()}")
            
            # Listar primeras 10 tablas
            print("\n  Listando primeras tablas disponibles en la BD:")
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """)
            tablas = cursor.fetchall()
            print(f"  Total de tablas encontradas: {len(tablas)}")
            for t in tablas[:15]:
                print(f"    - {t[0]}")
            if len(tablas) > 15:
                print(f"    ... y {len(tablas) - 15} tablas más.")
                
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"  [FALLO] con {{{driver}}}: {e}")
            
    print("\n[!] No se pudo conectar. Verifica que:")
    print("1. El servicio de SQL Server 2000 esté corriendo.")
    print("2. TCP/IP esté habilitado en 'SQL Server Network Utility' en el servidor.")
    print("3. El puerto (usualmente 1433) esté abierto en el Firewall.")
    print("4. Las credenciales en .env sean correctas.")
    return False


if __name__ == "__main__":
    test_connection()

