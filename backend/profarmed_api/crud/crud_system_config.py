"""
Operaciones CRUD para system_configs (Configuraciones Operacionales del Sistema)
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from db.base import SystemConfig
from schemas.system_config import SystemConfigUpdate


def get_system_configs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> Tuple[List[SystemConfig], int]:
    """
    Obtiene la lista de configuraciones del sistema con paginación y búsqueda server-side.
    Retorna (items, total_count).
    """
    query = db.query(SystemConfig)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SystemConfig.config_name.ilike(search_term),
                SystemConfig.description.ilike(search_term)
            )
        )

    total_count = query.count()
    items = query.order_by(SystemConfig.config_id.asc()).offset(skip).limit(limit).all()
    return items, total_count


def get_system_config_by_id(db: Session, config_id: int) -> Optional[SystemConfig]:
    """Obtiene una configuración por su config_id"""
    return db.query(SystemConfig).filter(SystemConfig.config_id == config_id).first()


def update_system_config_active(
    db: Session,
    config_id: int,
    config_update: SystemConfigUpdate
) -> Optional[SystemConfig]:
    """
    Actualiza exclusivamente el campo is_active de una configuración del sistema.
    """
    config_obj = db.query(SystemConfig).filter(SystemConfig.config_id == config_id).first()
    if not config_obj:
        return None

    was_active = config_obj.is_active
    config_obj.is_active = config_update.is_active

    # Si se desactiva la regla 101 (order.apartar), limpiar automáticamente todos los apartados
    if (config_id == 101 or config_obj.config_name == "order.apartar") and (was_active and not config_update.is_active):
        from db.base import OrderStockHold
        db.query(OrderStockHold).delete(synchronize_session=False)

    # Si se modifica la regla 107 (pricing.tax_inclusive), invalidar caché de precios
    if config_id == 107 or config_obj.config_name == "pricing.tax_inclusive":
        try:
            from utils.price_utils import clear_tax_inclusive_cache
            clear_tax_inclusive_cache()
        except Exception:
            pass

    db.commit()
    db.refresh(config_obj)
    return config_obj


def seed_default_system_configs(db: Session, default_tax_inclusive: bool = False) -> None:
    """
    Garantiza que las configuraciones estándar 101 a 107 existan en system_configs.
    Idempotente: inserta las que falten sin alterar las existentes.
    """
    defaults = [
        (101, 'order.apartar', 'Aparta provisionalmente el stock de los productos al crear pedidos web hasta que se aprueben o sincronicen con el ERP SAI.', False),
        (102, 'order.discount', 'Descuenta inmediatamente las existencias del catálogo web en cuanto se crea un pedido antes del proceso en almacén/SAI.', False),
        (103, 'catalog.order_by_priority', 'Prioriza en el catálogo y filtros por defecto los productos con display_priority manual (1 a 999,999) y después los generales.', True),
        (104, 'catalog.weekly_rotation', 'Habilita la rotación y barajado periódico de productos sin prioridad personalizada (>= 1,000,000) para dar variedad visual al cliente.', False),
        (105, 'user.auto_create_sales_group', 'Crea automáticamente un grupo de ventas vinculado al registrar o sincronizar un nuevo colaborador/usuario interno.', True),
        (106, 'customer.auto_assign_agent_group', 'Asigna automáticamente al cliente al grupo comercial de su agente/vendedor asignado al crear, actualizar o sincronizar.', True),
        (107, 'pricing.tax_inclusive', 'Indica que los precios de listas ya incluyen IVA (modelo neto mostrador/farmacia). Al estar activo, no suma IVA adicional en catálogo ni checkout y desglosa el impuesto hacia abajo.', default_tax_inclusive),
    ]

    for cid, name, desc, active in defaults:
        exists = db.query(SystemConfig).filter(SystemConfig.config_id == cid).first()
        if not exists:
            new_cfg = SystemConfig(
                config_id=cid,
                config_name=name,
                description=desc,
                is_active=active
            )
            db.add(new_cfg)
    try:
        db.commit()
    except Exception:
        db.rollback()
