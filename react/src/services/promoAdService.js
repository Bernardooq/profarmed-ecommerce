import apiService from './apiService';

const promoAdService = {
  /**
   * (Cliente Autenticado) Obtiene las secciones de publicidad activas ordenadas
   * Retorna { has_ads: boolean, sections: Array }
   */
  getActiveAds: async () => {
    return await apiService.get('/promo-ads/active', { _options: { noRedirect: true } });
  },

  /**
   * (Admin) Obtiene todas las secciones y anuncios de publicidad de inicio
   * @param {Object} params Parámetros (skip, limit)
   */
  getSections: async (params = {}) => {
    return await apiService.get('/promo-ads/', params);
  },

  /**
   * (Admin) Crea una nueva sección publicitaria (1 a 4 columnas)
   * @param {Object} sectionData Datos de la sección
   */
  createSection: async (sectionData) => {
    return await apiService.post('/promo-ads/sections', sectionData);
  },

  /**
   * (Admin) Actualiza el orden vertical de múltiples secciones
   * @param {Array<{section_id: string, display_order: number}>} sections Lista de órdenes
   */
  reorderSections: async (sections) => {
    return await apiService.put('/promo-ads/sections/reorder', { sections });
  },

  /**
   * (Admin) Actualiza una sección existente
   * @param {string} sectionId UUID de la sección
   * @param {Object} updateData Campos a actualizar
   */
  updateSection: async (sectionId, updateData) => {
    return await apiService.put(`/promo-ads/sections/${sectionId}`, updateData);
  },

  /**
   * (Admin) Elimina una sección y todos sus anuncios e imágenes en S3
   * @param {string} sectionId UUID de la sección
   */
  deleteSection: async (sectionId) => {
    return await apiService.delete(`/promo-ads/sections/${sectionId}`);
  },

  /**
   * (Admin) Agrega un anuncio a una columna (slot) de la sección
   * @param {string} sectionId UUID de la sección padre
   * @param {Object} itemData Datos del anuncio
   */
  createItem: async (sectionId, itemData) => {
    return await apiService.post(`/promo-ads/sections/${sectionId}/items`, itemData);
  },

  /**
   * (Admin) Actualiza un anuncio individual
   * @param {string} itemId UUID del anuncio
   * @param {Object} updateData Campos a actualizar
   */
  updateItem: async (itemId, updateData) => {
    return await apiService.put(`/promo-ads/items/${itemId}`, updateData);
  },

  /**
   * (Admin) Elimina un anuncio individual y sus imágenes en S3
   * @param {string} itemId UUID del anuncio
   */
  deleteItem: async (itemId) => {
    return await apiService.delete(`/promo-ads/items/${itemId}`);
  },

  /**
   * (Admin) Sube una imagen responsiva al bucket de promos en formato WebP
   * @param {File} file Archivo de imagen
   * @param {'desktop'|'tablet'|'mobile'} variant Variante de pantalla
   */
  uploadImage: async (file, variant = 'desktop') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('variant', variant);
    return await apiService.postForm('/promo-ads/upload-image', formData);
  },

  /**
   * (Admin) Elimina una imagen huérfana de S3 dentro de promo-ads/
   * @param {string} imgKey Clave S3 (ej. promo-ads/desktop/xxx.webp)
   */
  deleteImage: async (imgKey) => {
    return await apiService.delete(`/promo-ads/image?img_key=${encodeURIComponent(imgKey)}`);
  }
};

export default promoAdService;
