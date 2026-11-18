"""
Routes Maestras para el Subsistema de Almacén y Surtido (Warehouse Management System v2.2)

Proporciona la infraestructura completa de fulfillment para operaciones de bodega física:
- Cola FIFO y monitoreo en tiempo real de pedidos listos para surtido.
- Particionamiento atómico en Splits y asignación de colaboradores (Surtidor / Revisor).
- Terminal de surtido guiado por láser con pistolas USB/Bluetooth, cámara WebRTC y cajas maestras.
- Gestión física y ciclo de vida de Canastas QR reutilizables (Totes).
- Auditoría forense en tiempo real, detección de discrepancias y doble filtro de verificación.

ARQUITECTURA DE SUB-ROUTERS:
- dispatch.py: Despacho y enrutamiento inicial de pedidos hacia piso de almacén.
- queue.py: Cola FIFO de órdenes, métricas en vivo, historial y directorio de operarios.
- containers.py: Parque físico de canastas QR, asignación, disponibilidad y retiro.
- splits.py: Gestión de splits, autoasignación, cambio de modalidad y máquina de estados.
- operations.py: Operaciones de pistoleo láser en piso, cajas cerradas y validaciones manuales.
- audit.py: Auditoría forense, bitácora de eventos (Event Ledger) y rectificaciones administrativas.

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
('warehouse.view', 'warehouse.operator', 'warehouse.checker', 'warehouse.send', 
 'warehouse.filter2_send', 'warehouse.seal_direct', 'warehouse.mode_direct',
 'warehouse.mode_containers', 'warehouse.supervisor', 'warehouse.manage', 'warehouse.audit', 'system.admin')
"""

from fastapi import APIRouter

from .dispatch import router as dispatch_router
from .queue import router as queue_router
from .containers import router as containers_router
from .splits import router as splits_router
from .operations import router as operations_router
from .audit import router as audit_router

router = APIRouter()

router.include_router(dispatch_router)
router.include_router(queue_router)
router.include_router(containers_router)
router.include_router(splits_router)
router.include_router(operations_router)
router.include_router(audit_router)

__all__ = ["router"]
