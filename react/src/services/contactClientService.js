import apiService from './apiService';

export const contactClientService = {
  // === CONTACT MESSAGES ===
  async getContactMessages(params = {}) {
    return apiService.get('/contact/admin/all', params);
  },

  async updateContactStatus(id, status) {
    return apiService.patch(`/contact/${id}`, { status });
  },

  async deleteContactMessage(id) {
    return apiService.delete(`/contact/${id}`);
  },

  // === CLIENT REQUESTS ===
  async getClientRequests(params = {}) {
    return apiService.get('/client-request/admin/all', params);
  },

  async getClientRequestDocUrl(id, docType) {
    return apiService.get(`/client-request/admin/${id}/download/${docType}`);
  },

  async updateClientRequestStatus(id, status) {
    return apiService.patch(`/client-request/admin/${id}/status`, { status });
  },

  async deleteClientRequest(id) {
    return apiService.delete(`/client-request/admin/${id}`);
  }
};

export default contactClientService;
