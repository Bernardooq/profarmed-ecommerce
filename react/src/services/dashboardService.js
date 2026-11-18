import apiService from './apiService'

/**
 * Servicio para métricas y estadísticas operativas de grupos comerciales y dashboard
 */
export const dashboardService = {
    async getOperationalStats(salesGroupId = null) {
        const params = salesGroupId ? { sales_group_id: salesGroupId } : {}
        return apiService.get('/admindash/dashboard/operational', params)
    },
    async getOrderStats(salesGroupId = null) {
        const params = salesGroupId ? { sales_group_id: salesGroupId } : {}
        return apiService.get('/admindash/dashboard/orders', params)
    },
    async getInventoryStats() {
        return apiService.get('/admindash/dashboard/inventory')
    },
    async getFinanceStats() {
        return apiService.get('/admindash/dashboard/finance')
    },
    async getUsersCustomersStats() {
        return apiService.get('/admindash/dashboard/users-customers')
    }
}

export default dashboardService
