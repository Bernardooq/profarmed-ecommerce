import apiService from './apiService'
import BRAND from '../config/brand'

// Servicio para todo lo que un admin puede hacer (stats, usuarios, etc.)
export const adminService = {

  // Obtener las estadísticas del dashboard

  // Obtener top productos anuales en O(1)
  async getTopProducts(year = null, sortBy = 'orders', limit = 5) {
    const params = { sort_by: sortBy, limit }
    if (year) params.year = year
    return apiService.get('/admindash/dashboard/top-products', params)
  },

  async getDashboardStats() {
    return apiService.get('/admindash/dashboard')
  },

  // ==================== Dashboards Desacoplados (PBAC) ====================
  // Métricas financieras anuales (Ingresos, Ganancia)
  async getDashboardFinanceStats() {
    return apiService.get('/admindash/dashboard/finance')
  },

  // Embudo de pedidos y estados de órdenes
  async getDashboardOrderStats(salesGroupId = null) {
    const params = salesGroupId ? { sales_group_id: salesGroupId } : {}
    return apiService.get('/admindash/dashboard/orders', params)
  },

  // Personal y clientes registrados (clientes + desglose por roles)
  async getDashboardUsersCustomersStats() {
    return apiService.get('/admindash/dashboard/users-customers')
  },

  // Salud del catálogo e inventario (total, bajo stock, agotados)
  async getDashboardInventoryStats() {
    return apiService.get('/admindash/dashboard/inventory')
  },

  // ==================== Gestión de usuarios ====================

  // Traer usuarios con filtros opcionales (paginación, rol, búsqueda, etc.)
  async getUsers(params = {}) {
    return apiService.get('/admin/users', params)
  },

  // Obtener usuarios filtrados por rol
  async getUsersByRole(role, params = {}) {
    return this.getUsers({ ...params, role })
  },

  // Obtener un usuario específico por su ID
  async getUserById(id) {
    return apiService.get(`/admin/users/${id}`)
  },

  // Crear un nuevo usuario (dato normal: esto sí se manda como JSON)
  async createUser(userData) {
    return apiService.post('/admin/users', userData)
  },

  // Editar un usuario existente
  async updateUser(id, userData) {
    return apiService.put(`/admin/users/${id}`, userData)
  },

  // Eliminar un usuario por su ID
  async deleteUser(id) {
    return apiService.delete(`/admin/users/${id}`)
  },

  // Cambiar rol de usuario operativo dinámico
  async changeUserRole(id, role) {
    return apiService.put(`/admin/users/${id}/role`, { role })
  },

  // Promover o cambiar rol de usuario (soporta rol específico o toggle)
  async promoteUser(id, targetRole = null) {
    if (targetRole) {
      return apiService.put(`/admin/users/${id}/role`, { role: targetRole })
    }
    return apiService.put(`/admin/users/${id}/promote`)
  },

  // Asignar masivamente grupos a un colaborador comercial
  async assignUserGroups(id, groupIds) {
    return apiService.put(`/sales-groups/users/${id}/groups`, { group_ids: groupIds })
  },

  // ==================== Roles y Permisos (RBAC Dinámico) ====================

  // Obtener catálogo de permisos del sistema (sólo lectura)
  async getPermissions() {
    return apiService.get('/roles/permissions')
  },

  // Listar todos los roles configurados
  async getRoles() {
    return apiService.get('/roles')
  },

  // Obtener detalle de un rol específico con sus permisos
  async getRoleById(id) {
    return apiService.get(`/roles/${id}`)
  },

  // Crear un nuevo rol personalizado
  async createRole(roleData) {
    return apiService.post('/roles', roleData)
  },

  // Actualizar un rol existente
  async updateRole(id, roleData) {
    return apiService.put(`/roles/${id}`, roleData)
  },

  // Eliminar un rol personalizado
  async deleteRole(id) {
    return apiService.delete(`/roles/${id}`)
  },

  // Asignar o sincronizar matriz de permisos de un rol
  async assignRolePermissions(id, permissionSlugs) {
    return apiService.post(`/roles/${id}/permissions`, { permission_slugs: permissionSlugs })
  },

  // ==================== Reportes ====================

  // Obtener reporte de ventas por rango de fechas
  async getSalesReport(startDate, endDate) {
    return apiService.get('/admindash/reports/sales', {
      start_date: startDate,
      end_date: endDate
    })
  },

  // ==================== Exportaciones ====================

  // Descargar XLSX con data del sistema por tipo (solo admin)
  // exportType: 'clientes' | 'vendedores' | 'marketing' | 'grupos' | 'productos' | 'precios'
  async exportXLSX(exportType, extraParams = {}) {
    const { API_BASE } = await import('../config/api')
    const token = localStorage.getItem('token')
    const qs = new URLSearchParams({ type: exportType })
    Object.entries(extraParams).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') qs.append(k, v)
    })
    const response = await fetch(`${API_BASE}/admin/export-xlsx?${qs.toString()}`, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Error desconocido' }))
      throw new Error(err.detail || 'Error al exportar datos')
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const disposition = response.headers.get('Content-Disposition')
    a.download = disposition?.split('filename=')[1] || `${BRAND.slug}_${exportType}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  // ==================== Configuraciones del Sistema (system_configs) ====================
  async getSystemConfigs(params = {}) {
    return apiService.get('/system-configs', params)
  },

  async updateSystemConfigStatus(configId, isActive) {
    return apiService.put(`/system-configs/${configId}`, { is_active: isActive })
  }
}

export default adminService
