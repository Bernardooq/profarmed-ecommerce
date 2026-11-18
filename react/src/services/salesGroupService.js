import apiService from './apiService';

const salesGroupService = {
  // Sales Groups CRUD
  async getSalesGroups(params = {}) {
    return apiService.get('/sales-groups/', params);
  },

  async getSalesGroup(groupId) {
    return apiService.get(`/sales-groups/${groupId}`);
  },

  async createSalesGroup(groupData) {
    return apiService.post('/sales-groups/', groupData);
  },

  async updateSalesGroup(groupId, groupData) {
    return apiService.put(`/sales-groups/${groupId}`, groupData);
  },

  async deleteSalesGroup(groupId) {
    return apiService.delete(`/sales-groups/${groupId}`);
  },

  // Miembros y Usuarios del Grupo (PBAC / RBAC Dinámico)
  async getGroupMembers(groupId, params = {}) {
    return apiService.get(`/sales-groups/${groupId}/members`, params);
  },

  async getAvailableMembers(groupId, params = {}) {
    return apiService.get(`/sales-groups/${groupId}/available-members`, params);
  },

  async assignMemberToGroup(groupId, userId) {
    return apiService.post(`/sales-groups/${groupId}/members`, { user_id: userId });
  },

  async removeMemberFromGroup(groupId, userId) {
    return apiService.delete(`/sales-groups/${groupId}/members/${userId}`);
  },

  // Obtener usuarios colaboradores del grupo (ej: asignación en pedidos y clientes)
  async getUsersByGroup(groupId, params = {}) {
    return this.getGroupMembers(groupId, params);
  },

  async getGroupAgents(groupId, params = {}) {
    return this.getGroupMembers(groupId, params);
  },

  // Clientes asignados al grupo
  async getGroupCustomers(groupId, params = {}) {
    return apiService.get(`/sales-groups/${groupId}/customers`, params);
  },

  async getAvailableCustomers(groupId, params = {}) {
    return apiService.get(`/sales-groups/${groupId}/available-customers`, params);
  },

  async assignCustomerToGroup(groupId, customerId) {
    return apiService.post(`/sales-groups/${groupId}/customers/${customerId}`);
  },

  async removeCustomerFromGroup(groupId, customerId) {
    return apiService.delete(`/sales-groups/${groupId}/customers/${customerId}`);
  },

  // Mis Grupos asignados
  async getMyGroups(params = {}) {
    return apiService.get('/sales-groups/my-groups', params);
  },

  // IDs de grupos de un usuario
  async getUserGroupIds(userId) {
    return apiService.get(`/sales-groups/users/${userId}/groups`);
  },

  // Asignación masiva atómica de grupos a un usuario
  async bulkAssignUserGroups(userId, groupIds) {
    return apiService.put(`/sales-groups/users/${userId}/groups`, { group_ids: groupIds });
  },
};

export default salesGroupService;
