import apiService from './apiService'
import { API_BASE } from '../config/api'

// Servicio para manejar todo lo del carrito y las órdenes
export const orderService = {

  // ==================== Carrito ====================

  // Obtener los productos que el usuario tiene en su carrito
  async getCart() {
    return apiService.get('/orders/cart')
  },

  // Agregar un producto al carrito (por defecto añade 1)
  async addToCart(productId, quantity = 1) {
    return apiService.post('/orders/cart', {
      product_id: productId,
      quantity
    })
  },

  // Actualizar la cantidad de un producto en el carrito
  async updateCartItem(cartId, quantity) {
    return apiService.put(`/orders/cart/${cartId}`, { quantity })
  },

  // Eliminar un item del carrito
  async removeCartItem(cartId) {
    return apiService.delete(`/orders/cart/${cartId}`)
  },

  // Vaciar completamente el carrito
  async clearCart() {
    return apiService.delete('/orders/cart')
  },

  // Importar productos al carrito desde un archivo Excel
  async importCartExcel(file) {
    const formData = new FormData()
    formData.append('file', file)
    return apiService.postForm('/orders/cart/import-excel', formData)
  },

  // ==================== Órdenes ====================

  // Crear una orden a partir del carrito
  async checkout(shippingAddressNumber = 1, orderNotes = '', invoiceType = 'factura') {
    return apiService.post('/orders/checkout', {
      shipping_address_number: shippingAddressNumber,
      order_notes: orderNotes || null,
      invoice_type: invoiceType || 'factura'
      // shipping_cost será manejado por el backend
    })
  },

  // Obtener las órdenes del usuario actual (con filtros como paginación o estatus)
  async getOrders(params = {}) {
    return apiService.get('/orders/', params)
  },

  // Obtener todas las órdenes (colaboradores comerciales y roles con 'orders.view')
  async getAllOrders(params = {}) {
    return apiService.get('/orders/all', params)
  },

  // Obtener detalles de una orden en específico
  async getOrderById(id) {
    return apiService.get(`/orders/${id}`)
  },

  // Obtener detalles completos de una orden con relaciones (alias explícito)
  async getOrderDetails(id) {
    return apiService.get(`/orders/${id}/details`)
  },

  // Cambiar el estatus de una orden (roles con capacidad 'orders.status')
  async updateOrderStatus(id, status) {
    return apiService.put(`/orders/${id}/status`, { status })
  },

  // Cancelar una orden
  async cancelOrder(id) {
    return apiService.post(`/orders/${id}/cancel`)
  },

  // Asignar colaborador/asesor a una orden (roles con capacidad 'orders.assign')
  async assignOrder(id, userId, notes = '') {
    return apiService.post(`/orders/${id}/assign`, {
      assigned_user_id: userId,
      assignment_notes: notes
    })
  },

  // Editar items de una orden (roles con capacidad 'orders.edit')
  async editOrder(id, editData) {
    return apiService.put(`/orders/${id}/edit`, editData)
  },

  // Actualizar estado de sincronización ERP de un pedido
  async updateOrderSync(id, isSynced = true) {
    return apiService.patch(`/sync-upload/orders/${id}/sync`, { is_synced: isSynced })
  },

  // Crear pedido para un cliente (roles con capacidad 'orders.create')
  async createOrderForCustomer(orderData) {
    return apiService.post('/orders/create-for-customer', orderData)
  },

  // Descargar pedido en formato TXT (o ZIP comprimido si se divide por partes)
  async downloadOrderTXT(orderId, itemsPerFile = null) {
    const token = localStorage.getItem('token')
    let url = `${API_BASE}/orders/${orderId}/download-txt`
    if (itemsPerFile && itemsPerFile > 0) {
      url += `?items_per_file=${itemsPerFile}`
    }

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
      throw new Error(errorData.detail || 'Error al descargar el archivo')
    }

    const blob = await response.blob()

    // Detección precisa de archivo ZIP (vía Content-Type o inspección de magic bytes PK)
    const contentType = response.headers.get('Content-Type') || response.headers.get('content-type') || ''
    let isZip = contentType.includes('zip')
    
    if (!isZip && blob.size >= 4) {
      try {
        const headerSlice = await blob.slice(0, 4).arrayBuffer()
        const bytes = new Uint8Array(headerSlice)
        // 0x50, 0x4B ('PK') identifican archivos ZIP
        if (bytes[0] === 0x50 && bytes[1] === 0x4B) {
          isZip = true
        }
      } catch {
        // Fallback silencioso si no se puede leer el slice
      }
    }

    // Detectar el nombre de archivo desde el header Content-Disposition si está disponible
    let filename = ''
    const disposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition')
    if (disposition && disposition.includes('filename')) {
      const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i)
      if (filenameMatch && filenameMatch[1]) {
        filename = decodeURIComponent(filenameMatch[1].trim())
      }
    }

    // Si no se obtuvo filename desde los headers del servidor o debe corregirse
    if (!filename) {
      if (isZip || (itemsPerFile && itemsPerFile > 0)) {
        filename = `pedido_${orderId}_partes.zip`
      } else {
        filename = `pedido_${orderId}.txt`
      }
    } else if (isZip && !filename.toLowerCase().endsWith('.zip')) {
      // Si el archivo es un ZIP pero el nombre extraído carece de extensión .zip
      filename = filename.replace(/\.[^/.]+$/, '') + '.zip'
    } else if (!isZip && filename.toLowerCase().endsWith('.zip')) {
      // Si NO es un ZIP real (es texto), evitar que se guarde como .zip
      filename = filename.replace(/\.zip$/i, '.txt')
    }

    // Crear blob y forzar tipo application/zip si corresponde
    const finalBlob = isZip ? new Blob([blob], { type: 'application/zip' }) : blob
    const blobUrl = window.URL.createObjectURL(finalBlob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(blobUrl)
  }
}

export default orderService
