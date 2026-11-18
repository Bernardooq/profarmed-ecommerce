import apiService from './apiService'

// Servicio para todo lo relacionado con productos
export const productService = {

  // Traer productos con filtros opcionales (paginación, categoría, búsqueda, etc.)
  async getProducts(params = {}) {
    return apiService.get('/products/', params)
  },

  // Obtener un producto por su ID
  async getProductById(id) {
    return apiService.get(`/products/${id}`)
  },

  // Obtener un producto por su codebar (a veces es más útil que el ID)
  async getProductBycodebar(codebar) {
    return apiService.get(`/products/codebar/${codebar}`)
  },

  // Crear un nuevo producto
  async createProduct(productData) {
    return apiService.post('/products', productData)
  },

  // Editar un producto existente
  async updateProduct(id, productData) {
    return apiService.put(`/products/${id}`, productData)
  },

  // Actualizar solo la imagen del producto
  async updateProductImage(id, imageUrl) {
    return apiService.patch(`/products/${id}/image`, { image_url: imageUrl })
  },

  // Actualizar stock (puede ser positivo o negativo)
  async updateStock(id, quantity) {
    return apiService.patch(`/products/${id}/stock`, { quantity })
  },

  // Obtener apartados activos (order_stock_holds) de un producto
  async getProductStockHolds(productId, params = {}) {
    return apiService.get(`/products/${productId}/stock-holds`, params)
  },

  // Eliminar/liberar un apartado específico de un pedido para este producto
  async deleteProductStockHold(productId, orderId) {
    return apiService.delete(`/products/${productId}/stock-holds/${orderId}`)
  },

  // Eliminar un producto por ID
  async deleteProduct(id) {
    return apiService.delete(`/products/${id}`)
  },

  // Obtener productos similares basados en componentes activos
  async getSimilarProducts(productId, priceListId = null, limit = 5, minSimilarity = 0.3) {
    const params = { limit, min_similarity: minSimilarity }
    if (priceListId) {
      params.price_list_id = priceListId
    }
    return apiService.get(`/products/${productId}/similar`, params)
  },

  // Subir una imagen de producto a S3, devuelve { image_url }
  async uploadImage(productId, file) {
    const formData = new FormData()
    formData.append('product_id', productId)
    formData.append('file', file)
    return apiService.postForm('/products/upload-image', formData)
  },

  // Barajar productos sin prioridad fija (display_priority >= 1,000,000)
  async shuffleCatalog() {
    return apiService.post('/products/shuffle-catalog')
  }
}

export default productService
