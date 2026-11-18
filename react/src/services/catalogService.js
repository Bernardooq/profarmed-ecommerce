import apiService from './apiService'

let publicPriceListsCache = null;
let publicPriceListsCacheAt = 0;
let publicPriceListsInFlight = null;
const PUBLIC_LISTS_CACHE_MS = 30000;

const catalogService = {
    async getProducts(params = {}) {
        return apiService.get('/catalog/products', params);
    },
    async getCatalogProducts(params = {}) {
        return apiService.get('/catalog/products', params);
    },
    async getProduct(productId) {
        return apiService.get(`/catalog/products/${productId}`);
    },
    async getCustomerCatalogProducts(customerId, params = {}) {
        return apiService.get(`/catalog/customer/${customerId}/products`, params);
    },
    async getCustomerRecommendations(customerId, limit = 12, productId) {
        const params = { limit };
        params.product_id = productId;
        return apiService.get(`/catalog/customer/${customerId}/recommendations`, params);
    },
    async getProductSimilar(customerId, productId, limit = 8) {
        return apiService.get(`/catalog/customer/${customerId}/products/${productId}/similar`, { limit });
    },

    /**
     * Obtiene las listas de precios públicas para storefront general (sin requerir sesión).
     * Deduplica llamadas simultáneas para optimizar Header, Footer y Catálogo Público.
     */
    async getPublicPriceLists(forceRefresh = false) {
        const now = Date.now();
        if (!forceRefresh && publicPriceListsCache !== null && (now - publicPriceListsCacheAt) < PUBLIC_LISTS_CACHE_MS) {
            return publicPriceListsCache;
        }
        if (!forceRefresh && publicPriceListsInFlight) {
            return publicPriceListsInFlight;
        }
        publicPriceListsInFlight = apiService.get('/catalog/public/price-lists', { _options: { noRedirect: true } })
            .then((lists) => {
                publicPriceListsCache = Array.isArray(lists) ? lists : [];
                publicPriceListsCacheAt = Date.now();
                return publicPriceListsCache;
            })
            .finally(() => {
                publicPriceListsInFlight = null;
            });
        return publicPriceListsInFlight;
    },

    /**
     * Obtiene los productos paginados de una lista de precios pública storefront
     */
    async getPublicProducts(params = {}) {
        return apiService.get('/catalog/public/products', { ...params, _options: { noRedirect: true } });
    },

    /**
     * Obtiene el detalle público de un producto individual si existe lista pública storefront activa
     */
    async getPublicProduct(productId, priceListId = null) {
        const params = { _options: { noRedirect: true } };
        if (priceListId) {
            params.price_list_id = priceListId;
        }
        return apiService.get(`/catalog/public/products/${encodeURIComponent(productId)}`, params);
    },

    /**
     * Export customer's product catalog to XLSX
     * Triggers a file download
     */
    async exportProducts() {
        const { API_BASE } = await import('../config/api');
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/catalog/products/export`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Error desconocido' }));
            throw new Error(err.detail || 'Error al exportar el catálogo');
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const disposition = response.headers.get('Content-Disposition');
        a.download = disposition?.split('filename=')[1] || 'catalogo.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
};

export { catalogService };
export default catalogService;
