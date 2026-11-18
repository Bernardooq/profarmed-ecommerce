/**
 * Products.jsx
 * ============
 * Página de catálogo de productos de Profarmed
 * 
 * Funcionalidades:
 * - Vista dual: Modo E-Commerce (Grid) vs Modo Punto de Venta (POS corporativo)
 * - Configurador de columnas / campos estilo ServiceNow (guardado en LocalStorage)
 * - Búsqueda, filtrado por categoría, ordenamiento
 * - Paginación de resultados
 * - Modal de detalles del producto y carrito integrado
 * 
 * Permisos: Requiere autenticación
 */

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faThLarge, faTable, faSlidersH } from '@fortawesome/free-solid-svg-icons';

import { productService } from '../services/productService';
import catalogService from '../services/catalogService';
import { categoryService } from '../services/categoryService';
import { useAuth } from '../context/AuthContext';
import { useCatalogSettings } from '../hooks/useCatalogSettings';
import usePermissions from '../hooks/usePermissions';

import SearchBar from '../components/layout/SearchBar';
import Header2 from '../components/layout/Header2';
import StoriesBar from '../components/announcements/StoriesBar';
import HelpGuide from '../components/common/HelpGuide';
import Footer from '../components/layout/Footer';
import FiltersBar from '../components/products/FiltersBar';
import ProductGrid from '../components/products/ProductGrid';
import PosCatalogView from '../components/products/PosCatalogView';
import ColumnPickerModal from '../components/products/ColumnPickerModal';
import PaginationButtons from '../components/common/PaginationButtons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import ModalProductDetails from '../components/modals/products/ModalProductDetails';

const PRODUCTS_PER_PAGE = 12;

export default function Products() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { 
    viewMode, 
    setViewMode, 
    visibleColumns, 
    setVisibleColumns,
    toggleColumn, 
    resetColumns, 
    isColumnVisible, 
    allColumns 
  } = useCatalogSettings();

  const searchQuery = searchParams.get('search') || '';

  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [isColumnPickerOpen, setIsColumnPickerOpen] = useState(false);

  const [selectedCategory, setSelectedCategory] = useState('');
  const [sortOrder, setSortOrder] = useState('relevance');
  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);

  const [prevSearchQuery, setPrevSearchQuery] = useState(searchQuery);
  if (searchQuery !== prevSearchQuery) {
    setPrevSearchQuery(searchQuery);
    setPage(0);
  }

  const { isAuthenticated, isCustomer, isStaff } = usePermissions();

  const handleExportCatalog = useCallback(async () => {
    try {
      await catalogService.exportProducts();
    } catch (err) {
      setError(err.message || 'Error al exportar el catálogo');
      console.error(err);
    }
  }, []);

  const isInternalUser = isStaff;

  useEffect(() => { loadCategories(); }, []);
  useEffect(() => { loadProducts(); }, [selectedCategory, sortOrder, page, searchQuery, isCustomer, isInternalUser]);

  const loadCategories = async () => {
    try {
      const data = await categoryService.getCategories();
      setCategories(data);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const loadProducts = async () => {
    if (!user) {
      setProducts([]);
      setLoading(false);
      setError('Debes iniciar sesión para ver el catálogo de productos.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const params = {
        skip: page * PRODUCTS_PER_PAGE,
        limit: PRODUCTS_PER_PAGE,
        ...(selectedCategory && { category_id: selectedCategory }),
        ...(searchQuery && { search: searchQuery })
      };

      let data;

      if (isCustomer) {
        const sortConfig = {
          'price_asc': { sort_by: 'price', sort_order: 'asc' },
          'price_desc': { sort_by: 'price', sort_order: 'desc' },
          'name_asc': { sort_by: 'name', sort_order: 'asc' },
          'name_desc': { sort_by: 'name', sort_order: 'desc' },
          'newest': { sort_by: 'created_at', sort_order: 'desc' },
          'relevance': {}
        };
        if (sortConfig[sortOrder]) Object.assign(params, sortConfig[sortOrder]);
        data = await catalogService.getProducts(params);
      } else if (isInternalUser) {
        params.is_active = true;
        const sortConfig = {
          'price_asc': { sort_by: 'price', sort_order: 'asc' },
          'price_desc': { sort_by: 'price', sort_order: 'desc' },
          'name_asc': { sort_by: 'name', sort_order: 'asc' },
          'name_desc': { sort_by: 'name', sort_order: 'desc' },
          'newest': { sort_by: 'created_at', sort_order: 'desc' },
          'relevance': {}
        };
        if (sortConfig[sortOrder]) Object.assign(params, sortConfig[sortOrder]);
        data = await productService.getProducts(params);
      } else {
        setError('Tu tipo de cuenta no tiene acceso al catálogo.');
        setLoading(false);
        return;
      }

      if (data && Array.isArray(data.items)) {
        setProducts(data.items);
        setLookaheadPages(data.lookahead_pages);
      } else {
        const isArray = Array.isArray(data);
        const list = isArray ? data : (data?.items || []);
        setProducts(list);
        setLookaheadPages(0);
      }
    } catch (err) {
      console.error('Error loading products:', err);
      const errorMsg = err.response?.data?.detail || err.detail || err.message || 'No se pudieron cargar los productos. Intenta de nuevo.';
      setError(errorMsg);
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryChange = (categoryId) => { setSelectedCategory(categoryId); setPage(0); };
  const handleSortChange = (newSortOrder) => { setSortOrder(newSortOrder); setPage(0); };
  const handleProductClick = (product) => { setSelectedProduct(product); setShowModal(true); };
  const handleCloseModal = () => { setShowModal(false); setSelectedProduct(null); };
  const handleClearSearch = () => { navigate('/products'); };

  return (
    <div className="page">
      <Helmet><meta name="robots" content="noindex, nofollow" /></Helmet>
      {isStaff ? <Header2 /> : <SearchBar />}
      <StoriesBar />

      <main className="page__content">
        <div className="page-container">
          {/* HEADER DEL CATÁLOGO + CONMUTADOR DE VISTAS */}
          <div className="catalog-header mb-6" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <h1 className="section-title">
                {searchQuery ? `Resultados para: "${searchQuery}"` : 'Catálogo de Productos'}
              </h1>
              <p className="text-muted text-sm" style={{ marginTop: '4px' }}>
                {viewMode === 'pos' 
                  ? 'Modo Punto de Venta: Diseñado para pedidos rápidos en ráfaga con carrito lateral.'
                  : 'Modo E-Commerce: Navegación visual tradicional por tarjetas de producto.'}
              </p>
            </div>

            <div className="catalog-header__actions" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {/* SELECTOR DE VISTA (DUAL MODE) */}
              <div className="view-mode-toggle">
                <button
                  type="button"
                  className={`btn-toggle-mode ${viewMode === 'ecommerce' ? 'active' : ''}`}
                  onClick={() => setViewMode('ecommerce')}
                  title="Modo E-Commerce (Tarjetas)"
                >
                  <FontAwesomeIcon icon={faThLarge} style={{ marginRight: '6px' }} />
                  Catálogo Visual
                </button>
                <button
                  type="button"
                  className={`btn-toggle-mode ${viewMode === 'pos' ? 'active' : ''}`}
                  onClick={() => setViewMode('pos')}
                  title="Modo Lista Rápida Punto de Venta"
                >
                  <FontAwesomeIcon icon={faTable} style={{ marginRight: '6px' }} />
                  Lista Rápida (POS)
                </button>
              </div>

              {isCustomer && (
                <button className="btn btn--primary btn--sm" onClick={handleExportCatalog} title="Descargar catálogo en Excel">
                  Descargar Catálogo
                </button>
              )}

              <HelpGuide
                title="Guía del Catálogo"
                items={[
                  "Modos de vista: Puedes alternar entre 'Catálogo Visual' (tarjetas) y 'Lista Rápida (POS)' (matriz corporativa).",
                  "Configurar Campos: En modo Punto de Venta, puedes elegir qué columnas mostrar (código, imagen, stock, precio, etc.).",
                  "Carrito Lateral: En Punto de Venta tienes el carrito en vivo a la derecha para agregar productos y ordenar al instante.",
                  "Filtros: Filtra por categoría o busca en tiempo real desde la barra de herramientas."
                ]}
              />
            </div>
          </div>

          {error && (
            <ErrorMessage error={error} onDismiss={() => setError(null)} />
          )}

          {searchQuery && (
            <div className="alert alert--info mb-4 d-flex items-center justify-between">
              <span>Mostrando {products.length} resultado(s) para "{searchQuery}"</span>
              <button onClick={handleClearSearch} className="btn btn--ghost btn--sm">
                Limpiar búsqueda
              </button>
            </div>
          )}

          {/* RENDERIZADO CONDICIONAL DE VISTA E-COMMERCE VS PUNTO DE VENTA */}
          {viewMode === 'pos' ? (
            <PosCatalogView
              products={products}
              loading={loading}
              categories={categories}
              selectedCategory={selectedCategory}
              setSelectedCategory={handleCategoryChange}
              sortOrder={sortOrder}
              onSortChange={handleSortChange}
              searchQuery={searchQuery}
              onSearchChange={(q) => navigate(q ? `/products?search=${encodeURIComponent(q)}` : '/products')}
              onProductClick={handleProductClick}
              isColumnVisible={isColumnVisible}
              openColumnPicker={() => setIsColumnPickerOpen(true)}
              onExportCatalog={isCustomer ? handleExportCatalog : null}
            />
          ) : (
            <>
              <FiltersBar
                categories={categories}
                selectedCategory={selectedCategory}
                onCategoryChange={handleCategoryChange}
                sortOrder={sortOrder}
                onSortChange={handleSortChange}
              />
              <br />
              <ProductGrid products={products} onProductClick={handleProductClick} />
            </>
          )}
        </div>

        <PaginationButtons
          currentPage={page}
          lookaheadPages={lookaheadPages}
          onPageChange={setPage}
        />
      </main>

      <ModalProductDetails
        product={selectedProduct}
        isOpen={showModal}
        onClose={handleCloseModal}
        onProductSelect={setSelectedProduct}
      />

      <ColumnPickerModal
        isOpen={isColumnPickerOpen}
        onClose={() => setIsColumnPickerOpen(false)}
        allColumns={allColumns}
        visibleColumns={visibleColumns}
        setVisibleColumns={setVisibleColumns}
        toggleColumn={toggleColumn}
        resetColumns={resetColumns}
      />

      <Footer />
    </div>
  );
}

