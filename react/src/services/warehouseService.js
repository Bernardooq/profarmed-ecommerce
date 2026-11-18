import apiService from './apiService';

/**
 * warehouseService.js
 * Servicio de comunicación con el backend para el Módulo de Bodega / Almacén (Warehouse Fulfillment).
 * Endpoints: /api/v1/warehouse/*
 */
const warehouseService = {
  /**
   * Obtener cola de trabajo FIFO de pedidos en bodega
   * @param {Object} params { skip, limit, warehouse_status, search, stage, assigned_to_me, audit_verdict }
   */
  async getQueue(params = {}) {
    return apiService.get('/warehouse/queue', params);
  },

  /**
   * Obtener historial general de pedidos de bodega
   * @param {Object} params { skip, limit, warehouse_status, search }
   */
  async getOrdersHistory(params = {}) {
    return apiService.get('/warehouse/orders/history', params);
  },

  /**
   * Obtener métricas y KPIs de bodega en tiempo real
   */
  async getStats() {
    return apiService.get('/warehouse/stats');
  },

  /**
   * Obtener detalle completo de un split y sus partidas físicas
   * @param {string} splitId UUID de el split
   */
  async getSplit(splitId) {
    return apiService.get(`/warehouse/splits/${splitId}`);
  },

  /**
   * Obtener detalle de un split por UUID o código de lote/split (ej. 105-1)
   * @param {string} code UUID o código split (ej. '105-1')
   */
  async getSplitByCode(code) {
    return apiService.get(`/warehouse/splits/by-code/${encodeURIComponent(code)}`);
  },

  /**
   * Autoasignarse o reclamar un split como picker o checker
   * @param {string} splitId UUID de el split
   * @param {string} roleType 'picker' | 'checker'
   * @param {boolean|null} usesContainers Si usa o no canastas QR
   */
  async claimSplit(splitId, roleType = 'picker', usesContainers = null) {
    const payload = { role_type: roleType };
    if (usesContainers !== null && usesContainers !== undefined) {
      payload.uses_containers = usesContainers;
    }
    return apiService.post(`/warehouse/splits/${splitId}/claim`, payload);
  },

  /**
   * Configurar modalidad del split (con o sin canastas QR)
   * @param {string} splitId UUID del split
   * @param {boolean} usesContainers True para canastas, False para surtido directo
   * @param {boolean} resetProgress Si se debe resetear el progreso a 0 al pasar a canastas
   */
  async setContainerMode(splitId, usesContainers, resetProgress = false) {
    return apiService.post(`/warehouse/splits/${splitId}/set-container-mode`, {
      uses_containers: Boolean(usesContainers),
      reset_progress: Boolean(resetProgress)
    });
  },

  /**
   * Obtener lista de operadores / almacenistas de bodega (Admin / Marketing)
   * @param {Object} params { skip, limit, search }
   */
  async getOperators(params = {}) {
    return apiService.get('/warehouse/operators', params);
  },

  /**
   * Reasignar split a otro usuario (Admin / Marketing)
   * @param {string} splitId UUID de el split
   * @param {string} roleType 'picker' | 'checker'
   * @param {string} targetUserId ID del usuario destino
   */
  async reassignSplit(splitId, roleType, targetUserId) {
    return apiService.post(`/warehouse/splits/${splitId}/reassign`, {
      role_type: roleType,
      target_user_id: targetUserId
    });
  },

  /**
   * Registrar escaneo láser de código de barras
   * @param {string} splitId UUID de el split
   * @param {string} codebar Código de barras escaneado
   * @param {string|null} containerQr Código QR de la canasta activa
   */
  async scanBarcode(splitId, codebar, containerQr = null) {
    const payload = { codebar };
    if (containerQr) payload.container_qr = containerQr;
    return apiService.post(`/warehouse/splits/${splitId}/scan-barcode`, payload);
  },

  /**
   * Registrar empaque masivo por cajas maestras (Master Boxes)
   * @param {string} splitId UUID de el split
   * @param {number} orderItemId ID del item de orden
   * @param {number} boxes Cantidad de cajas
   * @param {number} unitsPerBox Unidades por caja
   * @param {string|null} containerQr Código QR de la canasta activa
   */
  async addBoxes(splitId, orderItemId, boxes, unitsPerBox, containerQr = null) {
    const payload = {
      order_item_id: orderItemId,
      boxes: Number(boxes),
      units_per_box: Number(unitsPerBox)
    };
    if (containerQr) payload.container_qr = containerQr;
    return apiService.post(`/warehouse/splits/${splitId}/add-boxes`, payload);
  },

  /**
   * Registrar verificación manual con justificación forense
   * @param {string} splitId UUID de el split
   * @param {number} orderItemId ID del item de orden
   * @param {number} quantity Cantidad verificada manualmente
   * @param {string} reason Motivo justificado
   * @param {string|null} containerQr Código QR de la canasta activa
   */
  async addManual(splitId, orderItemId, quantity, reason, containerQr = null) {
    const numQty = Number(quantity);
    const payload = {
      order_item_id: orderItemId,
      quantity: numQty,
      manual_quantity: numQty,
      reason
    };
    if (containerQr) payload.container_qr = containerQr;
    return apiService.post(`/warehouse/splits/${splitId}/add-manual`, payload);
  },

  /**
   * Avanzar estatus de split y aplicar sello inviolable de seguridad
   * @param {string} splitId UUID de el split
   * @param {Object} data { security_seal_folio, new_status }
   */
  async advanceSplitStatus(splitId, data = {}) {
    return apiService.post(`/warehouse/splits/${splitId}/advance-status`, data);
  },

  /**
   * Confiar en el surtido y validar todo en el segundo filtro (Mesa de Control / Calidad)
   * @param {string} splitId UUID de el split
   */
  async checkerFastTrack(splitId) {
    return apiService.post(`/warehouse/splits/${splitId}/checker-fast-track`);
  },

  /**
   * Obtener reporte de auditoría forense del pedido
   * @param {number} orderId ID del pedido
   */
  async getAuditBreakdown(orderId, params = {}) {
    return apiService.get(`/warehouse/orders/${orderId}/audit-breakdown`, params);
  },

  /**
   * Enviar pedido a bodega particionando en N splits (Admin / Marketing)
   * @param {number} orderId ID del pedido
   * @param {number} totalSplits Número de splits (default: 1)
   */
  async sendToWarehouse(orderId, totalSplits = 1, showDetails = false) {
    return apiService.post(`/warehouse/orders/${orderId}/send-to-warehouse`, {
      total_splits: Number(totalSplits),
      show_details: Boolean(showDetails)
    });
  },

  /**
   * Alternar modo de visibilidad de bodega (Surtido Ciego vs Detallado) (Admin / Marketing)
   * @param {number} orderId ID del pedido
   * @param {boolean} showDetails True para mostrar detalles, False para surtido ciego
   */
  async toggleVisibility(orderId, showDetails) {
    return apiService.patch(`/warehouse/orders/${orderId}/visibility`, {
      show_details: Boolean(showDetails)
    });
  },

  /**
   * Cancelar envío de pedido a bodega (Admin / Marketing)
   * @param {number} orderId ID del pedido
   */
  async cancelWarehouse(orderId) {
    return apiService.post(`/warehouse/orders/${orderId}/cancel-warehouse`);
  },

  /**
   * Actualizar motivo o justificación de verificación manual de una partida (Admin, Marketing, Vendedor)
   * @param {string} orderItemId UUID de la partida
   * @param {string} manualReason Nuevo motivo o justificación
   */
  async updateOrderItemManualReason(orderItemId, manualReason) {
    return apiService.patch(`/warehouse/order-items/${orderItemId}/manual-reason`, {
      manual_reason: manualReason
    });
  },

  /**
   * Acción pericial de administrador para forzar estatus o rectificar sellos de split (Solo Admin)
   * @param {string} splitId UUID de el split
   * @param {Object} data { status, security_seal_folio, clear_seal }
   */
  async adminOverrideSplit(splitId, data = {}) {
    return apiService.patch(`/warehouse/splits/${splitId}/admin-override`, data);
  },

  /**
   * Acción pericial exclusiva de administrador para rectificar conteos de 1er y 2do filtro de una partida
   * @param {string} orderItemId UUID de la partida
   * @param {Object} data { scanned_prods, box_prods, manual_prods, manual_reason, checker_scanned_prods, checker_box_prods, checker_manual_prods, checker_manual_reason }
   */
  async adminOverrideItemCounts(orderItemId, data = {}) {
    return apiService.patch(`/warehouse/order-items/${orderItemId}/admin-override-counts`, data);
  },

  // ============================================================================
  // PARQUE FÍSICO DE CANASTAS QR (CONTAINERS / TOTES)
  // ============================================================================

  /**
   * Obtener métricas consolidadas del parque físico de canastas QR
   */
  async getContainersStats() {
    return apiService.get('/warehouse/containers/stats');
  },

  /**
   * Listar catálogo de canastas físicas QR con filtros opcionales
   * @param {Object} params { status, search, skip, limit }
   */
  async getContainers(params = {}) {
    return apiService.get('/warehouse/containers', params);
  },

  /**
   * Obtener detalle de una canasta física por ID
   * @param {number} containerId ID de la canasta
   */
  async getContainerById(containerId) {
    return apiService.get(`/warehouse/containers/${containerId}`);
  },

  /**
   * Obtener detalle de una canasta física por su código QR escaneado
   * @param {string} qrCode Código QR de la canasta
   */
  async getContainerByQr(qrCode) {
    return apiService.get(`/warehouse/containers/by-qr/${encodeURIComponent(qrCode)}`);
  },

  /**
   * Enrolar / registrar una nueva canasta física en el sistema
   * @param {string} qrCode Código QR o identificador de la canasta (ej: TOTE-001)
   */
  async createContainer(qrCode) {
    return apiService.post('/warehouse/containers', { qr_code: qrCode });
  },

  /**
   * Actualizar estatus físico de una canasta (available, in_use, maintenance)
   * @param {number} containerId ID de la canasta
   * @param {string} status 'available' | 'maintenance' | 'in_use'
   */
  async updateContainerStatus(containerId, status) {
    return apiService.put(`/warehouse/containers/${containerId}`, { status });
  },

  /**
   * Eliminar definitivamente una canasta del sistema (solo si no está en uso)
   * @param {number} containerId ID de la canasta
   */
  async deleteContainer(containerId) {
    return apiService.delete(`/warehouse/containers/${containerId}`);
  },

  /**
   * Liberar una canasta física desacoplándola del split y marcándola available
   * @param {Object} data { qr_code, container_id }
   */
  async releaseContainer(data = {}) {
    return apiService.post('/warehouse/containers/release', data);
  },

  /**
   * Vincular una canasta física QR a un split activo en terminal
   * @param {string} splitId UUID del split
   * @param {string} qrCode Código QR de la canasta
   */
  async bindContainerToSplit(splitId, qrCode) {
    return apiService.post(`/warehouse/splits/${splitId}/bind-container`, { qr_code: qrCode });
  },

  /**
   * Activar / Seleccionar una canasta física QR como la canasta de depósito actual
   * @param {string} splitId UUID del split
   * @param {string} qrCode Código QR de la canasta
   */
  async activateContainer(splitId, qrCode) {
    return apiService.post(`/warehouse/splits/${splitId}/activate-container`, { qr_code: qrCode });
  },

  // ============================================================================
  // BITÁCORA ATÓMICA DE ESCANEOS (EVENT LEDGER)
  // ============================================================================

  /**
   * Obtener bitácora forense de eventos de escaneo de un split
   * @param {string} splitId UUID del split
   * @param {Object} params { skip, limit }
   */
  async getSplitEvents(splitId, params = {}) {
    return apiService.get(`/warehouse/splits/${splitId}/events`, params);
  },

  /**
   * Obtener resumen consolidado y desglose de productos por canasta física de un split
   * @param {string} splitId UUID del split
   */
  async getSplitContainersSummary(splitId) {
    return apiService.get(`/warehouse/splits/${splitId}/containers-summary`);
  },

  /**
   * Obtener partidas consolidadas en canastas físicas de un split
   * @param {string} splitId UUID del split
   */
  async getSplitContainerItems(splitId) {
    return apiService.get(`/warehouse/splits/${splitId}/container-items`);
  }
};

export default warehouseService;
export { warehouseService };
