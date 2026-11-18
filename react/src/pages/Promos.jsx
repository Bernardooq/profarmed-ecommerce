/**
 * Promos.jsx
 * ==========
 * Vista de Ofertas y Promociones Especiales para el Cliente
 * 
 * Muestra exclusivamente productos que cuentan con descuentos activos
 * con paginación numérica Lookahead (Anterior 1 2 3 ... Siguiente).
 */

import { useState, useEffect, useCallback } from 'react';
import SEO from '../components/common/SEO';
import BRAND from '../config/brand';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faTag, faSearch, faPercent, faFire, 
  faBoxesStacked 
} from '@fortawesome/free-solid-svg-icons';

import catalogService from '../services/catalogService';
import { categoryService } from '../services/categoryService';
import { useAuth } from '../context/AuthContext';

import Header2 from '../components/layout/Header2';
import Footer from '../components/layout/Footer';
import ProductCard from '../components/products/ProductCard';
import ModalProductDetails from '../components/modals/products/ModalProductDetails';
import PaginationButtons from '../components/common/PaginationButtons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';

const PROMOS_PER_PAGE = 12;

export default function Promos() {
  const { user } = useAuth();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Paginación Lookahead
  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('discount_desc'); // discount_desc, price_asc, price_desc, name_asc

  // Modal de detalles
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // Debounce del input de búsqueda
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Carga inicial de categorías
  useEffect(() => {
    loadCategories();
  }, []);

  // Al cambiar filtros o búsqueda, volver a la primera página
  useEffect(() => {
    setPage(0);
  }, [debouncedSearch, selectedCategory, sortBy]);

  // Cargar promociones cuando cambie la página o filtros
  useEffect(() => {
    loadPromotions();
  }, [page, debouncedSearch, selectedCategory, sortBy]);

  const loadCategories = async () => {
    try {
      const data = await categoryService.getCategories();
      setCategories(data || []);
    } catch (err) {
      console.error('Error cargando categorías:', err);
    }
  };

  const loadPromotions = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        skip: page * PROMOS_PER_PAGE,
        limit: PROMOS_PER_PAGE,
        has_discount: true,
        ...(selectedCategory !== 'all' && { category_id: selectedCategory }),
        ...(debouncedSearch.trim() && { search: debouncedSearch.trim() })
      };

      const sortMap = {
        'discount_desc': { sort_by: 'discount', sort_order: 'desc' },
        'price_asc': { sort_by: 'price', sort_order: 'asc' },
        'price_desc': { sort_by: 'price', sort_order: 'desc' },
        'name_asc': { sort_by: 'name', sort_order: 'asc' }
      };
      if (sortMap[sortBy]) {
        Object.assign(params, sortMap[sortBy]);
      }

      const res = await catalogService.getProducts(params);
      const items = res?.items || res || [];
      const promoItems = Array.isArray(items) ? items.filter(p => p.has_discount === true) : [];
      setProducts(promoItems);
      setLookaheadPages(res?.lookahead_pages || 0);
    } catch (err) {
      console.error('Error cargando promociones:', err);
      setError('No pudimos cargar las promociones vigentes. Por favor intenta más tarde.');
      setProducts([]);
      setLookaheadPages(0);
    } finally {
      setLoading(false);
    }
  };

  const handleProductClick = (product) => {
    setSelectedProduct(product);
    setShowDetailsModal(true);
  };

  return (
    <div className="page">
      <SEO title={BRAND.getTitle('Ofertas & Promociones B2B')} description="Productos con descuento y precios especiales en medicamentos y farmacia para clientes mayoristas." noindex={true} />

      <Header2 user={user} />

      <main className="main-content promos-page">
        <div className="container promos-page__container">
          
          {/* Banner Hero de Promociones (Sin contador numérico) */}
          <div className="hero-promo-banner">
            <div className="hero-promo-banner__content">
              <div className="hero-promo-banner__tag">
                <FontAwesomeIcon icon={faFire} />
                OFERTAS EXCLUSIVAS B2B
              </div>
              <h1 className="hero-promo-banner__title">
                Precios Especiales & Descuentos
              </h1>
              <p className="hero-promo-banner__description">
                Aprovecha los descuentos activos aplicados directamente en tu lista de precios asignada. Los ahorros se aplican automáticamente en tu pedido.
              </p>
            </div>
          </div>

          {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

          {/* Barra de Filtros y Búsqueda */}
          <div className="promos-page__filters">
            {/* Buscador */}
            <div className="promos-page__search">
              <input
                type="text"
                className="input"
                placeholder="Buscar entre las promociones..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <FontAwesomeIcon icon={faSearch} className="promos-page__search-icon" />
            </div>

            {/* Categoría y Orden */}
            <div className="promos-page__select-group">
              <select
                className="input"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="all">Todas las Categorías</option>
                {categories.map(cat => (
                  <option key={cat.category_id} value={cat.category_id}>
                    {cat.name}
                  </option>
                ))}
              </select>

              <select
                className="input"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="discount_desc">Mayor Descuento</option>
                <option value="price_asc">Menor Precio</option>
                <option value="price_desc">Mayor Precio</option>
                <option value="name_asc">Nombre A-Z</option>
              </select>
            </div>
          </div>

          {/* Listado de Productos en Promoción */}
          {loading ? (
            <LoadingSpinner message="Consultando promociones disponibles para tu cuenta..." />
          ) : products.length === 0 ? (
            <div className="promos-page__empty-state">
              <div className="promos-page__empty-state-icon">
                <FontAwesomeIcon icon={faTag} size="2x" />
              </div>
              <h3 className="promos-page__empty-state-title">
                {debouncedSearch || selectedCategory !== 'all' 
                  ? 'No hay promociones con los filtros seleccionados' 
                  : 'No hay promociones activas en este momento'}
              </h3>
              <p className="promos-page__empty-state-desc">
                {debouncedSearch || selectedCategory !== 'all'
                  ? 'Intenta cambiar el término de búsqueda o seleccionar otra categoría.'
                  : 'Nuestro equipo actualiza periódicamente las ofertas y descuentos por lista. ¡Vuelve a consultar pronto!'}
              </p>
              {(debouncedSearch || selectedCategory !== 'all') && (
                <button 
                  className="btn btn--secondary" 
                  onClick={() => { setSearchTerm(''); setSelectedCategory('all'); }}
                >
                  Restablecer Filtros
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="product-grid promos-page__product-grid">
                {products.map((product) => (
                  <ProductCard 
                    key={product.product_id} 
                    product={product} 
                    onProductClick={handleProductClick} 
                  />
                ))}
              </div>

              {/* Botones de Paginación Idénticos al Catálogo */}
              <div className="promos-page__pagination-wrapper">
                <PaginationButtons
                  currentPage={page}
                  lookaheadPages={lookaheadPages}
                  onPageChange={setPage}
                />
              </div>
            </>
          )}
        </div>
      </main>

      {/* Modal de Detalle de Producto */}
      {showDetailsModal && selectedProduct && (
        <ModalProductDetails
          product={selectedProduct}
          isOpen={showDetailsModal}
          onClose={() => { setShowDetailsModal(false); setSelectedProduct(null); }}
        />
      )}

      <Footer />
    </div>
  );
}
