"""
Script de mantenimiento para PROFARMED.
Busca pedidos en estado 'approved' o 'shipped' que lleven más de un determinado número de días
(25 por defecto) desde su validación (o en su defecto, desde su creación) y los marca como 'delivered' (entregados).

Uso:
  python auto_deliver_old_orders.py --days 25 --date 2026-07-07
  python auto_deliver_old_orders.py --days 25 (usa la fecha actual como referencia)
"""

import sys
import os
import argparse
from datetime import datetime, timezone, timedelta
import pytz

# Añadir el directorio actual al path para importar modulos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import or_
from db.session import SessionLocal
from db.base import Order, OrderStatus
from crud.crud_order_stats import sync_order_on_status_change
from recalculate_order_stats import recalculate

def auto_deliver_old_orders(reference_date: datetime, days_limit: int):
    db = SessionLocal()
    try:
        print("=" * 80)
        print(f"INICIANDO AUTO-ENTREGA DE PEDIDOS MAYORES A {days_limit} DÍAS")
        print(f"Fecha de referencia (UTC): {reference_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Límite de tiempo: fecha de referencia menos N días
        limit_date = reference_date - timedelta(days=days_limit)
        print(f"-> Límite de antigüedad (anterior a): {limit_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # 1. Consultar pedidos aprobados o enviados
        print("-> Buscando pedidos en estado 'approved' o 'shipped'...")
        orders = db.query(Order).filter(
            Order.status.in_([OrderStatus.approved, OrderStatus.shipped])
        ).all()

        modified_count = 0
        
        for order in orders:
            # Determinación robusta de fecha de comparación:
            # 1. validated_at debe existir y ser mayor a created_at, de lo contrario usamos created_at como fallback
            if order.validated_at is not None and order.created_at is not None and order.validated_at > order.created_at:
                comp_date = order.validated_at
            else:
                comp_date = order.created_at
            
            # Asegurar que sea timezone aware en UTC para la comparación
            if comp_date.tzinfo is None:
                comp_date = comp_date.replace(tzinfo=timezone.utc)
            else:
                comp_date = comp_date.astimezone(timezone.utc)
                
            if comp_date < limit_date:
                old_status = order.status.value if hasattr(order.status, 'value') else order.status
                print(f"   [Pedido #{order.order_id}] Estado actual: '{old_status}', Ref. temporal: {comp_date.strftime('%Y-%m-%d')} -> Marcar como 'delivered'")
                
                # Actualizar estatus del pedido
                order.status = OrderStatus.delivered
                db.flush()
                
                # Sincronizar estadísticas individuales en tiempo real (afecta grupos y global)
                sync_order_on_status_change(
                    db, 
                    order.order_id, 
                    old_status, 
                    "delivered", 
                    order.customer_id
                )
                
                modified_count += 1
                
        if modified_count > 0:
            db.commit()
            print(f"✅ Se actualizaron {modified_count} pedidos a estado 'delivered'.")
            
            # 2. Recalcular estadísticas generales por seguridad para asegurar consistencia total
            print("-> Ejecutando recálculo completo de estadísticas para asegurar consistencia...")
            recalculate()
        else:
            print(f"ℹ️ No se encontraron pedidos aprobados o enviados con más de {days_limit} días de antigüedad.")
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el procesamiento: {e}")
        raise e
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(
        description="Pasa pedidos de 'approved' o 'shipped' a 'delivered' tras N días de inactividad."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=25,
        help="Días de antigüedad límite para entregar el pedido (por defecto 25)."
    )
    parser.add_argument(
        "--date",
        help="Fecha de referencia (YYYY-MM-DD). Si se omite, se usa la fecha actual."
    )
    args = parser.parse_args()

    mx_tz = pytz.timezone('America/Mexico_City')
    
    if args.date:
        try:
            parsed_date = datetime.strptime(args.date, "%Y-%m-%d")
            # Localizar el final del día en hora de México y convertir a UTC
            ref_date = mx_tz.localize(
                datetime.combine(parsed_date.date(), datetime.max.time())
            ).astimezone(timezone.utc)
        except ValueError:
            print("❌ Formato de fecha inválido. Utilice YYYY-MM-DD.")
            sys.exit(1)
    else:
        # Usar la hora actual en UTC
        ref_date = datetime.now(timezone.utc)

    auto_deliver_old_orders(ref_date, args.days)

if __name__ == "__main__":
    main()
