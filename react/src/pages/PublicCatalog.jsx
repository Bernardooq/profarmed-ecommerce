import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import SEO from '../components/common/SEO';
import { createBreadcrumbSchema, createCatalogItemListSchema } from '../utils/schemas';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faLayerGroup, faStore, faUserPlus, faSignInAlt } from '@fortawesome/free-solid-svg-icons';

import catalogService from '../services/catalogService';
import { categoryService } from '../services/categoryService';
import BRAND from '../config/brand';

import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import ProductGrid from '../components/products/ProductGrid';
import FiltersBar from '../components/products/FiltersBar';
import PaginationButtons from '../components/common/PaginationButtons';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import ModalProductDetails from '../components/modals/products/ModalProductDetails';

const PRODUCTS_PER_PAGE = 12;

export default function PublicCatalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Estados de Listas Públicas Storefront
  const [priceLists, setPriceLists] = useState([]);
  const [selectedPriceListId, setSelectedPriceListId] = useState(null);
  const [loadingLists, setLoadingLists] = useState(true);

  // Estados de Productos y Categorías
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [error, setError] = useState(null);

  // Paginación y Filtros
  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [sortOrder, setSortOrder] = useState('relevance');

  // Modal de detalles
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showModal, setShowModal] = useState(false);

  // Búsqueda
  const searchQuery = searchParams.get('search') || '';
  const [searchInput, setSearchInput] = useState(searchQuery);

  // 1. Cargar categorías y listas de precios públicas al montar
  useEffect(() => {
    loadCategories();
    loadPublicPriceLists();
  }, []);

  const loadCategories = async () => {
    try {
      const data = await categoryService.getCategories();
      setCategories(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error al cargar categorías en catálogo público:', err);
    }
  };

  const loadPublicPriceLists = async () => {
    try {
      setLoadingLists(true);
      const lists = await catalogService.getPublicPriceLists();
      const validLists = Array.isArray(lists) ? lists : [];
      setPriceLists(validLists);

      if (validLists.length > 0) {
        // Por defecto usar la primera lista pública
        const listParam = searchParams.get('list');
        const candidateId = listParam ? Number(listParam) : null;
        const exists = validLists.some(pl => pl.price_list_id === candidateId);
        setSelectedPriceListId(exists ? candidateId : validLists[0].price_list_id);
      } else {
        setSelectedPriceListId(null);
      }
    } catch (err) {
      console.error('Error al cargar listas de precios públicas:', err);
      setError('No se pudieron obtener las listas de precios públicas.');
    } finally {
      setLoadingLists(false);
    }
  };

  // 2. Cargar productos cada vez que cambien lista, categoría, orden, página o búsqueda
  useEffect(() => {
    if (selectedPriceListId) {
      loadProducts();
    }
  }, [selectedPriceListId, selectedCategory, sortOrder, page, searchQuery]);

  const loadProducts = async () => {
    try {
      setLoadingProducts(true);
      setError(null);

      const params = {
        price_list_id: selectedPriceListId,
        skip: page * PRODUCTS_PER_PAGE,
        limit: PRODUCTS_PER_PAGE,
        ...(selectedCategory && { category_id: selectedCategory }),
        ...(searchQuery && { search: searchQuery })
      };

      const sortConfig = {
        'price_asc': { sort_by: 'price', sort_order: 'asc' },
        'price_desc': { sort_by: 'price', sort_order: 'desc' },
        'name_asc': { sort_by: 'name', sort_order: 'asc' },
        'name_desc': { sort_by: 'name', sort_order: 'desc' },
        'newest': { sort_by: 'created_at', sort_order: 'desc' },
        'relevance': {}
      };
      if (sortConfig[sortOrder]) {
        Object.assign(params, sortConfig[sortOrder]);
      }

      const res = await catalogService.getPublicProducts(params);

      if (res && Array.isArray(res.items)) {
        setProducts(res.items);
        setLookaheadPages(res.lookahead_pages || 0);
      } else if (Array.isArray(res)) {
        setProducts(res);
        setLookaheadPages(0);
      } else {
        setProducts([]);
        setLookaheadPages(0);
      }
    } catch (err) {
      console.error('Error al cargar productos del catálogo público:', err);
      setError(err.message || 'No se pudieron cargar los productos del catálogo.');
      setProducts([]);
    } finally {
      setLoadingProducts(false);
    }
  };

  // Manejo de cambios
  const handlePriceListChange = (newPriceListId) => {
    setSelectedPriceListId(newPriceListId);
    setPage(0);
    const newParams = new URLSearchParams(searchParams);
    newParams.set('list', newPriceListId);
    setSearchParams(newParams);
  };

  const handleCategoryChange = (categoryId) => {
    setSelectedCategory(categoryId);
    setPage(0);
  };

  const handleSortChange = (newSortOrder) => {
    setSortOrder(newSortOrder);
    setPage(0);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const newParams = new URLSearchParams(searchParams);
    if (searchInput.trim()) {
      newParams.set('search', searchInput.trim());
    } else {
      newParams.delete('search');
    }
    setPage(0);
    setSearchParams(newParams);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    const newParams = new URLSearchParams(searchParams);
    newParams.delete('search');
    setPage(0);
    setSearchParams(newParams);
  };

  const handleProductClick = (product) => {
    setSelectedProduct(product);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedProduct(null);
  };

  const currentPriceListObj = priceLists.find(pl => pl.price_list_id === selectedPriceListId);
  const hasPublicStorefront = priceLists.length > 0;
  const catalogCanonical = BRAND.getCanonical('/catalogo');
  const shouldNoIndex = (!loadingLists && !hasPublicStorefront) || Boolean(searchQuery);

  const catalogSchemas = hasPublicStorefront && !searchQuery
    ? [
        createBreadcrumbSchema([
          { name: 'Inicio', url: `${BRAND.domain}/` },
          { name: 'Catálogo Público', url: catalogCanonical },
        ]),
        createCatalogItemListSchema(products, {
          catalogUrl: catalogCanonical,
          name: currentPriceListObj
            ? `Catálogo Público ${currentPriceListObj.list_name} - ${BRAND.name}`
            : `Catálogo Público - ${BRAND.name}`,
          description: `Catálogo abierto de productos y precios mayoristas de referencia en ${BRAND.name}.`,
        }),
      ]
    : null;

  return (
    <div className="page">
      <SEO
        title={BRAND.getTitle(searchQuery ? `Búsqueda: ${searchQuery}` : 'Catálogo Público de Productos')}
        description={
          currentPriceListObj?.description ||
          `Explora el catálogo abierto de productos farmacéuticos y medicamentos al mayoreo de ${BRAND.name}. Consulta disponibilidad y precios de referencia.`
        }
        keywords={`catálogo público, medicamentos al mayoreo, ${BRAND.name}, productos farmacéuticos B2B, precios de referencia`}
        canonical={catalogCanonical}
        ogType="website"
        noindex={shouldNoIndex}
        schema={catalogSchemas}
      />

      <Header />

      <main className="page__content">
        <div className="page-container">
          {/* HEADER DEL CATÁLOGO PÚBLICO */}
          <div className="catalog-header mb-6" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <div className="d-flex align-items-center gap-2 mb-1">
                <span className="badge badge--primary text-xs">
                  <FontAwesomeIcon icon={faStore} className="mr-1" />
                  Catálogo Abierto
                </span>
                {currentPriceListObj && (
                  <span className="badge badge--secondary text-xs">
                    {currentPriceListObj.list_name}
                  </span>
                )}
              </div>
              <h1 className="section-title mb-1">
                {searchQuery ? `Búsqueda: "${searchQuery}"` : 'Catálogo de Productos'}
              </h1>
              <p className="text-muted text-sm mb-0">
                Consulta los productos y precios de referencia disponibles para compras mayoristas.
              </p>
            </div>

            {/* SELECTOR DE LISTA DE PRECIOS (SI EXISTE MÁS DE 1) */}
            {priceLists.length > 1 && (
              <div className="filter-group__item" style={{ minWidth: '220px' }}>
                <label className="filter-group__label" htmlFor="select-public-list">
                  <FontAwesomeIcon icon={faLayerGroup} className="mr-1" />
                  Lista de Precios:
                </label>
                <select
                  id="select-public-list"
                  className="select"
                  value={selectedPriceListId || ''}
                  onChange={(e) => handlePriceListChange(Number(e.target.value))}
                >
                  {priceLists.map((pl) => (
                    <option key={pl.price_list_id} value={pl.price_list_id}>
                      {pl.list_name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* BARRA DE BÚSQUEDA PÚBLICA */}
          <div className="card p-4 mb-4 shadow-xs">
            <form onSubmit={handleSearchSubmit} className="d-flex gap-2 flex-wrap">
              <div style={{ flex: 1, minWidth: '240px', position: 'relative' }}>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="Buscar medicamentos por nombre, código de barras o descripción..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                />
              </div>
              <button type="submit" className="btn btn--primary">
                <FontAwesomeIcon icon={faSearch} className="mr-1" />
                Buscar
              </button>
              {searchQuery && (
                <button type="button" onClick={handleClearSearch} className="btn btn--ghost">
                  Limpiar filtro
                </button>
              )}
            </form>
          </div>

          {/* FILTROS DE CATEGORÍA Y ORDENAMIENTO */}
          <FiltersBar
            categories={categories}
            selectedCategory={selectedCategory}
            onCategoryChange={handleCategoryChange}
            sortOrder={sortOrder}
            onSortChange={handleSortChange}
          />
          <br />

          {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

          {/* ESTADO DE CARGA O CONTENIDO */}
          {loadingLists || loadingProducts ? (
            <LoadingSpinner message="Cargando catálogo de productos..." />
          ) : priceLists.length === 0 ? (
            <div className="card p-8 text-center max-w-lg mx-auto my-8">
              <h3 className="font-bold text-lg mb-2">Catálogo público no disponible</h3>
              <p className="text-muted mb-4">
                Actualmente no hay listas de precios configuradas para acceso público general.
                Si ya eres cliente registrado, inicia sesión para acceder a tus precios autorizados.
              </p>
              <div className="d-flex justify-center gap-3">
                <Link to="/login" className="btn btn--primary btn--sm">
                  <FontAwesomeIcon icon={faSignInAlt} className="mr-1" />
                  Iniciar Sesión
                </Link>
                <Link to="/quiero-ser-cliente" className="btn btn--secondary btn--sm">
                  <FontAwesomeIcon icon={faUserPlus} className="mr-1" />
                  Quiero ser cliente
                </Link>
              </div>
            </div>
          ) : products.length === 0 ? (
            <div className="card p-8 text-center my-6">
              <p className="text-muted text-base mb-3">No se encontraron productos con los criterios seleccionados.</p>
              {(searchQuery || selectedCategory) && (
                <button onClick={() => { handleClearSearch(); setSelectedCategory(''); }} className="btn btn--secondary btn--sm">
                  Restablecer filtros
                </button>
              )}
            </div>
          ) : (
            <>
              {/* GRILLA DE PRODUCTOS CON AGREGAR AL CARRITO DESACTIVADO */}
              <ProductGrid
                products={products}
                onProductClick={handleProductClick}
                allowAddToCart={false}
                getProductUrl={(p) => `/catalogo/producto/${encodeURIComponent(p.product_id)}`}
              />

              <PaginationButtons
                currentPage={page}
                lookaheadPages={lookaheadPages}
                onPageChange={setPage}
              />
            </>
          )}

          {/* BANNER INFORMATIVO / CTA PARA VISITANTES */}
          <div className="card p-6 mt-8 shadow-sm" style={{ background: 'var(--color-surface)', borderLeft: '4px solid var(--color-primary)' }}>
            <div className="d-flex justify-content-between align-items-center flex-wrap gap-4">
              <div>
                <h3 className="font-bold text-lg mb-1">¿Deseas comprar a mayoreo y levantar pedidos en línea?</h3>
                <p className="text-muted text-sm mb-0">
                  Regístrate como cliente farmacéutico para acceder a tus listas personalizadas, descuentos exclusivos y entrega directa.
                </p>
              </div>
              <div className="d-flex gap-2">
                <Link to="/quiero-ser-cliente" className="btn btn--primary">
                  <FontAwesomeIcon icon={faUserPlus} className="mr-1" />
                  Quiero ser cliente
                </Link>
                <Link to="/login" className="btn btn--ghost">
                  <FontAwesomeIcon icon={faSignInAlt} className="mr-1" />
                  Iniciar Sesión
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* MODAL DETALLES DEL PRODUCTO */}
      <ModalProductDetails
        product={selectedProduct}
        isOpen={showModal}
        onClose={handleCloseModal}
        onProductSelect={setSelectedProduct}
        allowAddToCart={false}
      />

      <Footer />
    </div>
  );
}
