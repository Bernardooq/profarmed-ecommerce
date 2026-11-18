import apiService from './apiService';

export const userService = {
  // Obtener perfil del usuario actual
  async getCurrentUser() {
    return apiService.get('/users/me');
  },

  // Actualizar perfil del usuario actual
  async updateCurrentUser(userData) {
    return apiService.put('/users/me', userData);
  },

  // Obtener información de cliente del usuario actual
  async getCurrentUserCustomerInfo() {
    return apiService.get('/users/me/customer-info');
  },

  // Admin: Obtener información de cliente de un usuario específico
  async getUserCustomerInfo(userId) {
    return apiService.get(`/admin/users/${userId}/customer-info`);
  },

  // Admin: Actualizar información de cliente de un usuario específico
  async updateUserCustomerInfo(userId, customerInfoData) {
    return apiService.put(`/admin/users/${userId}/customer-info`, customerInfoData);
  },

  // Obtener lista general de usuarios con filtros dinámicos (rol, búsqueda, paginación)
  async getUsers(params = {}) {
    return apiService.get('/users', params);
  },

  // Obtener usuarios filtrados por cualquier rol dinámico (ej: 'seller', 'mark', 'cadenero', etc.)
  async getUsersByRole(role, params = {}) {
    return apiService.get('/users', { ...params, role });
  },

  // Obtener usuarios filtrados por código de permiso PBAC (ej: 'orders.create', 'warehouse.operator')
  async getUsersByPermission(permissionCode, params = {}) {
    return apiService.get('/users', { ...params, permission_code: permissionCode });
  },

  // Obtener usuarios colaboradores disponibles (agnóstico a roles fijos)
  async getAvailableUsers(params = {}) {
    return this.getUsers({ limit: 100, ...params });
  },
};

