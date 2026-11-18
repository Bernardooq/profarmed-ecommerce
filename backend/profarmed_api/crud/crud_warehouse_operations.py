"""
Fachada de Operaciones de Piso y Escaneo de Almacén (Warehouse Operations Facade):

Este módulo unifica y re-exporta las sub-unidades operativas desacopladas:
- `crud_warehouse_splits.py`: Búsqueda, autoasignación, modalidad con/sin canastas y reasignación de lotes/splits.
- `crud_warehouse_scanning.py`: Terminal láser de piso, empaque por cajas maestras y validación manual.
- `crud_warehouse_containers.py`: Parque físico, asignaciones de canastas QR, distribución física y bitácora.
"""

from crud.crud_warehouse_splits import (
    _get_split_model,
    get_split_by_id,
    get_split_by_code,
    claim_split,
    set_split_container_mode,
    reassign_split,
    _validate_split_operator_permissions,
)

from crud.crud_warehouse_scanning import (
    scan_barcode_laser,
    add_boxes_master,
    add_manual_verification,
)

from crud.crud_warehouse_containers import (
    _record_container_item,
    get_split_container_items,
    get_split_containers_summary,
    list_warehouse_containers,
    get_warehouse_container_by_id,
    get_warehouse_container_by_qr,
    create_warehouse_container,
    update_warehouse_container_status,
    bind_container_to_split,
    activate_container_for_split,
    release_warehouse_container,
    delete_warehouse_container,
)

__all__ = [
    # Split queries and assignment
    "_get_split_model",
    "get_split_by_id",
    "get_split_by_code",
    "claim_split",
    "set_split_container_mode",
    "reassign_split",
    "_validate_split_operator_permissions",
    # Floor scanning and verification
    "scan_barcode_laser",
    "add_boxes_master",
    "add_manual_verification",
    # Container operations and summaries
    "_record_container_item",
    "get_split_container_items",
    "get_split_containers_summary",
    "list_warehouse_containers",
    "get_warehouse_container_by_id",
    "get_warehouse_container_by_qr",
    "create_warehouse_container",
    "update_warehouse_container_status",
    "bind_container_to_split",
    "activate_container_for_split",
    "release_warehouse_container",
    "delete_warehouse_container",
]
