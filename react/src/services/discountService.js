import apiService from './apiService';

const discountService = {
  /**
   * Obtener lista de descuentos con filtros opcionales (paginados por backend)
   */
  async getDiscounts(params = {}) {
    return apiService.get('/discounts', params);
  },

  /**
   * Obtener métricas y KPIs globales de descuentos (Server-side)
   */
  async getDiscountStats() {
    return apiService.get('/discounts/stats');
  },

  /**
   * Obtener un descuento específico por ID
   */
  async getDiscount(discountId) {
    return apiService.get(`/discounts/${discountId}`);
  },

  /**
   * Obtener descuento activo para un producto y lista de precios
   */
  async getActiveDiscount(productId, priceListId = null) {
    const params = priceListId ? { price_list_id: priceListId } : {};
    return apiService.get(`/discounts/active/${productId}`, params);
  },

  /**
   * Crear un nuevo descuento (Admin)
   */
  async createDiscount(data) {
    return apiService.post('/discounts', data);
  },

  /**
   * Actualizar un descuento existente (Admin)
   */
  async updateDiscount(discountId, data) {
    return apiService.put(`/discounts/${discountId}`, data);
  },

  /**
   * Eliminar un descuento (Admin)
   */
  async deleteDiscount(discountId) {
    return apiService.delete(`/discounts/${discountId}`);
  }
};

export default discountService;
export { discountService };
