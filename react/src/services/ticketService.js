import apiService from './apiService';

export const ticketService = {
  // Obtener lista de tickets (filtrados automagicamente en backend segun rol)
  async getTickets(params = {}) {
    return apiService.get('/tickets', params);
  },

  // Obtener un ticket especifico con todos sus mensajes
  async getTicket(id) {
    return apiService.get(`/tickets/${id}`);
  },

  // Crear un nuevo ticket
  async createTicket(ticketData) {
    return apiService.post('/tickets', ticketData);
  },

  // Agregar mensaje al ticket
  async addMessage(id, content) {
    return apiService.post(`/tickets/${id}/messages`, { content });
  },

  // Cambiar el estado del ticket (requiere 'support.manage')
  async updateStatus(id, status) {
    return apiService.put(`/tickets/${id}/status`, { status });
  },

  // Escalar el ticket a Admin (requiere 'support.manage')
  async escalateTicket(id) {
    return apiService.put(`/tickets/${id}/escalate`);
  },

  // Desescalar el ticket (requiere 'support.deescalate')
  async deEscalateTicket(id) {
    return apiService.put(`/tickets/${id}/de-escalate`);
  },

  // Tomar/Asignarse el ticket (requiere 'support.manage')
  async assignTicket(id) {
    return apiService.put(`/tickets/${id}/assign`);
  }
};

export default ticketService;
