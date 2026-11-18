import apiService from './apiService';

const announcementService = {
  /**
   * Obtiene la lista de anuncios
   * @param {Object} params Parámetros (skip, limit)
   */
  getAnnouncements: async (params = {}) => {
    return await apiService.get('/admin/announcements/', params);
  },

  /**
   * Crea un nuevo anuncio
   * @param {Object} announcementData Datos del anuncio
   */
  createAnnouncement: async (announcementData) => {
    return await apiService.post('/admin/announcements/', announcementData);
  },

  /**
   * Actualiza un anuncio existente
   * @param {number} id ID del anuncio
   * @param {Object} updateData Datos a actualizar
   */
  updateAnnouncement: async (id, updateData) => {
    return await apiService.put(`/admin/announcements/${id}`, updateData);
  },

  /**
   * Elimina un anuncio
   * @param {number} id ID del anuncio
   */
  deleteAnnouncement: async (id) => {
    return await apiService.delete(`/admin/announcements/${id}`);
  },

  /**
   * Sube una imagen al bucket de promos y devuelve la key (URL de S3)
   * @param {File} file Archivo de imagen
   */
  uploadPromoImage: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return await apiService.postForm('/admin/announcements/upload-image', formData);
  },

  /**
   * (Público) Obtiene un anuncio popup activo al azar
   */
  getPopup: async () => {
    return await apiService.get('/public/announcements/popup');
  },

  /**
   * (Público) Obtiene un anuncio footer activo al azar
   */
  getFooter: async () => {
    return await apiService.get('/public/announcements/footer');
  },

  /**
   * (Privado/Cliente) Obtiene hasta 100 stories activas al azar
   */
  getStories: async () => {
    return await apiService.get('/public/announcements/stories', { _options: { noRedirect: true } });
  },

  /**
   * Envía un anuncio por correo electrónico a todos los clientes que aceptaron notificaciones
   * @param {number} id ID del anuncio
   */
  sendAnnouncement: async (id) => {
    return await apiService.post(`/admin/announcements/${id}/send`);
  }
};

export default announcementService;
