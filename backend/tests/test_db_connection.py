"""
Verificación de Conexión a Base de Datos PostgreSQL
Prueba la conectividad con la base de datos configurada en las variables de entorno.
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

def test_connection():
    try:
        from dotenv import load_dotenv
        load_dotenv(backend_dir / ".env")
    except ImportError:
        pass
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️ No se encontró la variable DATABASE_URL en el entorno o .env.")
        print("Configura DATABASE_URL para probar la conexión.")
        return False

    safe_url = db_url.split("@")[-1] if "@" in db_url else "configurado"
    print(f"🔄 Conectando a PostgreSQL ({safe_url})...")
    
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).scalar()
            print("✅ Conexión exitosa a PostgreSQL!")
            print(f"   Versión del motor: {res[:80]}")
            
            tables_res = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)).fetchall()
            tables = [r[0] for r in tables_res]
            print(f"   Tablas públicas detectadas ({len(tables)}): {', '.join(tables[:10])}{'...' if len(tables) > 10 else ''}")
            return True
    except Exception as e:
        print(f"❌ Error al conectar con la base de datos: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
