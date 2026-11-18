"""
Script de mantenimiento para PROFARMED.
Recalcula y sincroniza la tabla order_stats desde cero leyendo todos los pedidos existentes.
"""

import sys
import os

# Añadir el directorio actual al path para importar modulos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import func
from db.session import SessionLocal
from db.base import Order, OrderStat, CustomerInfo

def recalculate():
    db = SessionLocal()
    try:
        print("Iniciando recalculado de estadísticas de pedidos...")
        
        # 1. Limpiar tabla existente
        deleted = db.query(OrderStat).delete()
        print(f"Limpieza completada. Registros eliminados de order_stats: {deleted}")
        
        # 2. Conteo global (sales_group_id = 0) para Admin
        print("Calculando estadísticas globales (Admin)...")
        global_stats = db.query(Order.status, func.count(Order.order_id).label('cnt')).group_by(Order.status).all()
        for row in global_stats:
            status_val = row.status.value if hasattr(row.status, 'value') else row.status
            db.add(OrderStat(sales_group_id=0, status=status_val, count=row.cnt))
            print(f"  - Global (ID: 0) -> Estado: {status_val}, Total: {row.cnt}")
            
        # 3. Conteo por Grupo de Ventas (sales_group_id > 0)
        print("Calculando estadísticas por Grupo de Ventas...")
        group_stats = db.query(
            CustomerInfo.sales_group_id,
            Order.status,
            func.count(Order.order_id).label('cnt')
        ).join(
            Order, CustomerInfo.customer_id == Order.customer_id
        ).filter(
            CustomerInfo.sales_group_id != None
        ).group_by(
            CustomerInfo.sales_group_id, Order.status
        ).all()
        
        for row in group_stats:
            status_val = row.status.value if hasattr(row.status, 'value') else row.status
            db.add(OrderStat(sales_group_id=row.sales_group_id, status=status_val, count=row.cnt))
            print(f"  - Grupo (ID: {row.sales_group_id}) -> Estado: {status_val}, Total: {row.cnt}")
            
        db.commit()
        print("Sincronización finalizada con éxito. Todos los datos de order_stats fueron guardados.")
    except Exception as e:
        db.rollback()
        print(f"Error inesperado durante la ejecución: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    recalculate()
