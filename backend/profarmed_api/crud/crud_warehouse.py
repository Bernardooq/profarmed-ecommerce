"""
CRUD y Fachada Principal de Almacén y Bodega (Warehouse v2.2) — PBAC & RBAC Dinámico:

Arquitectura Modular del Subsistema de Bodega:
- `crud_warehouse_orders.py`: Enrutamiento, visibilidad FIFO, control de órdenes, borrado en cascada y parque de canastas QR.
- `crud_warehouse_operations.py`: Gestión de splits, escaneo láser en piso y validación física.
- `crud_warehouse_status.py`: Ciclo de vida de estados, sellos inviolables y recálculo pericial.
- `crud_warehouse_audit.py`: Trazabilidad forense, métricas operativas y overrides de inventario.

Permisos PBAC Exportados y Requeridos:
- Visualización de pedidos y colas: `warehouse.view`
- Surtido físico en piso (1er Filtro / Picker): `warehouse.operator`
- Revisión en mesa de control (2do Filtro / Checker): `warehouse.checker`, `warehouse.operator`
- Supervisión operativa y métricas: `warehouse.supervisor`, `warehouse.manage`, `orders.approve`
- Gestión, reasignación, canastas QR y cancelación: `warehouse.manage`, `warehouse.containers`, `system.admin`
- Auditoría forense pericial, bitácora atómica y overrides: `warehouse.audit`, `warehouse.events`, `warehouse.manage`, `system.admin`
"""

from crud.crud_warehouse_orders import (
    send_order_to_warehouse,
    toggle_order_warehouse_visibility,
    cancel_order_warehouse,
    cleanup_warehouse_for_order,
    get_warehouse_queue,
    get_warehouse_orders_history,
    list_warehouse_containers,
    get_warehouse_containers_stats,
    get_warehouse_container_by_id,
    get_warehouse_container_by_qr,
    create_warehouse_container,
    update_warehouse_container_status,
    bind_container_to_split,
    activate_container_for_split,
    release_warehouse_container,
    delete_warehouse_container,
)

from crud.crud_warehouse_operations import (
    get_split_by_id,
    get_split_by_code,
    claim_split,
    set_split_container_mode,
    reassign_split,
    scan_barcode_laser,
    add_boxes_master,
    add_manual_verification,
    _validate_split_operator_permissions,
    get_split_containers_summary,
    get_split_container_items,
)

from crud.crud_warehouse_status import (
    advance_split_status,
    fast_track_approve_second_filter,
    sync_warehouse_on_order_edit,
    _recalculate_order_warehouse_status,
)

from crud.crud_warehouse_audit import (
    get_order_warehouse_audit,
    get_warehouse_stats,
    update_order_item_manual_reason,
    admin_override_split,
    admin_override_order_item_counts,
)

__all__ = [
    # Orders & Queue & Cascade Cleanup
    "send_order_to_warehouse",
    "toggle_order_warehouse_visibility",
    "cancel_order_warehouse",
    "cleanup_warehouse_for_order",
    "get_warehouse_queue",
    "get_warehouse_orders_history",
    # QR Containers (Totes)
    "list_warehouse_containers",
    "get_warehouse_containers_stats",
    "get_warehouse_container_by_id",
    "get_warehouse_container_by_qr",
    "create_warehouse_container",
    "update_warehouse_container_status",
    "bind_container_to_split",
    "release_warehouse_container",
    "delete_warehouse_container",
    # Floor Operations
    "get_split_by_id",
    "get_split_by_code",
    "claim_split",
    "reassign_split",
    "scan_barcode_laser",
    "add_boxes_master",
    "add_manual_verification",
    "_validate_split_operator_permissions",
    # Status & Seals
    "advance_split_status",
    "fast_track_approve_second_filter",
    "sync_warehouse_on_order_edit",
    "_recalculate_order_warehouse_status",
    # Audit & Admin
    "get_order_warehouse_audit",
    "get_warehouse_stats",
    "update_order_item_manual_reason",
    "admin_override_split",
    "admin_override_order_item_counts",
]
