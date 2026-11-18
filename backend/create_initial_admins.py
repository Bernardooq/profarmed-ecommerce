"""
Script para crear los 4 usuarios administradores iniciales de Profarmed
Uso (desde la carpeta backend): python create_initial_admins.py
"""
import sys
import os

# Agregar el directorio profarmed_api al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'profarmed_api'))

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from db.session import SessionLocal
    from db.base import User
    from core.security import get_password_hash
    from core.config import DATABASE_URL
except ImportError as e:
    print(f"Error al importar modulos: {e}")
    print("\nAsegurate de:")
    print("1. Estar en la carpeta 'backend'")
    print("2. Tener el entorno virtual activado")
    print("3. Haber instalado las dependencias: pip install -r requirements.txt")
    sys.exit(1)

# Definir los administradores
# Rangos de IDs: Admin 15,000,000+  |  Colaboradores comerciales/internos <15,000,000
ADMINS = [
    {
        "user_id": 15_000_001,
        "username": "bernardo.orozco",
        "email": "bernardo.orozco@profarmed.com.mx",
        "full_name": "Bernardo Orozco",
        "password": "profarmed2026"
    },
    {
        "user_id": 15_000_002,
        "username": "syncadminssuser2026",
        "email": "sync@profarmed.com.mx",
        "full_name": "Sync Admin",
        "password": "SyncProfarmed2026!Key"
    },
    {
        "user_id": 15_000_003,
        "username": "hector.admin",
        "email": "hector.admin@profarmed.com.mx",
        "full_name": "Héctor Admin",
        "password": "profarmed2026"
    },
    {
        "user_id": 15_000_004,
        "username": "demian.admin",
        "email": "demian.admin@profarmed.com.mx",
        "full_name": "Demian Admin",
        "password": "profarmed2026"
    },
    {
        "user_id": 15_000_005,
        "username": "profarmed.admin",
        "email": "profarmed.admin@profarmed.com.mx",
        "full_name": "Profarmed Admin",
        "password": "profarmed2026"
    },
    {
        "user_id": 15_000_007,
        "username": "admin1.demo",
        "email": "admin1.demo@profarmed.com.mx",
        "full_name": "Admin 1 Demo",
        "password": "profarmed2026"
    },
    {
        "user_id": 15_000_008,
        "username": "admin2.demo",
        "email": "admin2.demo@profarmed.com.mx",
        "full_name": "Admin 2 Demo",
        "password": "profarmed2026"
    }
]

def create_admin_users():
    """Crea los 4 usuarios administradores"""
    db: Session = SessionLocal()
    
    print("=" * 70)
    print("  CREACIoN DE USUARIOS ADMINISTRADORES - PROFARMED")
    print("=" * 70)
    print()
    
    # Verificar que todas las contraseñas esten asignadas
    missing_passwords = [admin["username"] for admin in ADMINS if not admin["password"]]
    if missing_passwords:
        print("ERROR: Las siguientes cuentas no tienen contraseña asignada:")
        for username in missing_passwords:
            print(f"   - {username}")
        print()
        print("Por favor, edita el archivo 'create_initial_admins.py' y asigna")
        print("las contraseñas en la lista ADMINS antes de ejecutar este script.")
        return False
    
    # Validar longitud de contraseñas
    weak_passwords = [
        admin["username"] for admin in ADMINS 
        if len(admin["password"]) < 8
    ]
    if weak_passwords:
        print("ERROR: Las siguientes cuentas tienen contraseñas muy cortas (minimo 8 caracteres):")
        for username in weak_passwords:
            print(f"   - {username}")
        return False
    
    created_count = 0
    skipped_count = 0
    
    try:
        for admin_data in ADMINS:
            try:
                # Verificar si el usuario ya existe
                existing_user = db.query(User).filter(
                    User.username == admin_data["username"]
                ).first()
                
                if existing_user:
                    existing_user.password_hash = get_password_hash(admin_data["password"])
                    existing_user.email = admin_data["email"]
                    existing_user.full_name = admin_data["full_name"]
                    existing_user.role_id = 1
                    existing_user.is_active = True
                    if hasattr(existing_user, "failed_login_attempts"):
                        existing_user.failed_login_attempts = 0
                    if hasattr(existing_user, "is_locked"):
                        existing_user.is_locked = False
                    if hasattr(existing_user, "locked_at"):
                        existing_user.locked_at = None
                    db.commit()
                    print(f"Usuario '{admin_data['username']}' ya existia - ACTUALIZADO con nueva contrasenia")
                    created_count += 1
                    continue
                
                # Crear el usuario
                hashed_password = get_password_hash(admin_data["password"])
                new_admin = User(
                    user_id=admin_data["user_id"],
                    username=admin_data["username"],
                    email=admin_data["email"],
                    password_hash=hashed_password,
                    full_name=admin_data["full_name"],
                    role_id=1,
                    is_active=True
                )
                
                db.add(new_admin)
                db.commit()
                db.refresh(new_admin)
                
                print(f"Usuario '{admin_data['username']}' creado exitosamente")
                print(f"   Email: {admin_data['email']}")
                print(f"   Nombre: {admin_data['full_name']}")
                print(f"   ID: {new_admin.user_id}")
                print()
                
                created_count += 1
                
            except Exception as user_error:
                print(f"Error al crear '{admin_data['username']}': {user_error}")
                db.rollback()
                continue
        
        print("=" * 70)
        print(f"  RESUMEN:")
        print(f"  - Usuarios creados: {created_count}")
        print(f"  - Usuarios omitidos (ya existian): {skipped_count}")
        print("=" * 70)
        print()
        
        if created_count > 0:
            print("Proceso completado exitosamente")
            print()
            print("IMPORTANTE:")
            print("   1. Guarda las credenciales en un lugar seguro")
            print("   2. Comparte las contraseñas de forma segura con cada usuario")
            print("   3. Pideles que cambien su contraseña en el primer login")
            print()
        
        return True
        
    except Exception as e:
        print(f"\nError durante la creacion de usuarios: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def verify_database_connection(max_retries=15, delay=2):
    """Verifica que la conexion a la base de datos funcione con reintentos para Docker"""
    import time
    print("Intentando conectar a PostgreSQL...")
    for attempt in range(1, max_retries + 1):
        try:
            db: Session = SessionLocal()
            db.execute(text("SELECT 1"))
            result = db.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            db.close()
            print(f"Conexion exitosa a PostgreSQL - {count} usuarios existentes en la base de datos\n")
            return True
        except Exception as e:
            if attempt < max_retries:
                print(f"Esperando a PostgreSQL (intento {attempt}/{max_retries})...")
                time.sleep(delay)
            else:
                print(f"No se pudo conectar a la base de datos tras {max_retries} intentos: {e}")
                return False

def main():
    # Verificar conexion
    if not verify_database_connection():
        print("Verifica la configuracion de la base de datos y vuelve a intentar.")
        return
    
    # Crear usuarios
    success = create_admin_users()
    
    if not success:
        print("\nEl proceso fallo. Revisa los errores anteriores.")
        exit(1)

if __name__ == "__main__":
    main()