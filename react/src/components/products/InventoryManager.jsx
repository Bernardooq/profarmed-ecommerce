import { useState, useEffect, useRef } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faPlus, faFileExport } from '@fortawesome/free-solid-svg-icons';
import { useAuth } from '../../context/AuthContext';
import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { productService } from '../../services/productService';
import { categoryService } from '../../services/categoryService';
import adminService from '../../services/adminService';
import ProductRow from './ProductRow';
import ModalAddProduct from '../modals/products/ModalAddProduct';
import ModalEditProduct from '../modals/products/ModalEditProduct';
import ModalViewProduct from '../modals/products/ModalViewProduct';
import ModalUpdateStock from '../modals/products/ModalUpdateStock';
import ModalProductStockHolds from '../modals/products/ModalProductStockHolds';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import PaginationButtons from '../common/PaginationButtons';
import usePermissions from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function InventoryManager() {
  const { user } = useAuth();
  const { limit: ITEMS_PER_PAGE } = usePaginationLimit();
  const { can, isAdmin } = usePermissions();
  const canViewCatalog = isAdmin || can(PERMISSIONS.CATALOG_VIEW);
  const canManageProducts = isAdmin || can(PERMISSIONS.CATALOG_MANAGE) || can(PERMISSIONS.PRODUCTS_CREATE);
  const canEditProducts = isAdmin || can(PERMISSIONS.PRODUCTS_EDIT) || can(PERMISSIONS.CATALOG_MANAGE);
  const canDeleteProducts = isAdmin || can(PERMISSIONS.PRODUCTS_DELETE);
  const canUpdateStock = isAdmin || can(PERMISSIONS.PRODUCTS_STOCK) || can(PERMISSIONS.PRODUCTS_EDIT);
  const canExport = isAdmin || can(PERMISSIONS.REPORTS_EXPORT);
  const canViewCost = isAdmin || can(PERMISSIONS.PRODUCTS_COST) || can(PERMISSIONS.CATALOG_PRICES);
  const canEditReservedStock = isAdmin || (can(PERMISSIONS.CATALOG_VIEW) && (can(PERMISSIONS.PRODUCTS_STOCK) || can(PERMISSIONS.PRODUCTS_EDIT)));

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [searchName, setSearchName] = useState('');
  const [debouncedSearchName, setDebouncedSearchName] = useState('');
  const [searchcodebar, setSearchcodebar] = useState('');
  const [debouncedSearchcodebar, setDebouncedSearchcodebar] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [stockFilter, setStockFilter] = useState('');
  const [imageFilter, setImageFilter] = useState('');
  const [isActiveFilter, setIsActiveFilter] = useState('true');
  const [sortBy, setSortBy] = useState('relevance');
  const [sortOrder, setSortOrder] = useState('asc');

  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);

  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showStockModal, setShowStockModal] = useState(false);
  const [showReservedStockModal, setShowReservedStockModal] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [previewImage, setPreviewImage] = useState(null);

  const categoriesLoaded = useRef(false);
  useEffect(() => {
    if (!categoriesLoaded.current) {
      loadCategories();
      categoriesLoaded.current = true;
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => { setDebouncedSearchName(searchName); setPage(0); }, 2500);
    return () => clearTimeout(timer);
  }, [searchName]);

  useEffect(() => {
    const timer = setTimeout(() => { setDebouncedSearchcodebar(searchcodebar); setPage(0); }, 2500);
    return () => clearTimeout(timer);
  }, [searchcodebar]);

  useEffect(() => {
    loadProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, selectedCategory, stockFilter, debouncedSearchName, debouncedSearchcodebar, imageFilter, isActiveFilter, sortBy, sortOrder, ITEMS_PER_PAGE]);

  const loadCategories = async () => {
    try {
      const data = await categoryService.getCategories();
      setCategories(data);
    } catch (err) { /* empty */ }
  };

  const loadProducts = async () => {
    if (!canViewCatalog) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const params = { skip: page * ITEMS_PER_PAGE, limit: ITEMS_PER_PAGE };
      if (debouncedSearchName) params.search = debouncedSearchName;
      if (debouncedSearchcodebar) params.codebar_search = debouncedSearchcodebar;
      if (selectedCategory) params.category_id = parseInt(selectedCategory);
      if (stockFilter) {
        const filterMap = { 'ok': 'in_stock', 'low': 'low_stock', 'out': 'out_of_stock', 'holds': 'with_holds' };
        params.stock_filter = filterMap[stockFilter];
      }
      if (imageFilter !== '') params.image = imageFilter === 'true';
      if (isActiveFilter === 'true') params.is_active = true;
      if (isActiveFilter === 'false') params.is_active = false;
      if (sortBy && sortBy !== 'relevance') params.sort_by = sortBy;
      if (sortOrder) params.sort_order = sortOrder;

      const data = await productService.getProducts(params);
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
      setError('No se pudieron cargar los productos. Intenta de nuevo.');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddProduct = async (productData) => {
    await productService.createProduct(productData);
    await loadProducts();
  };

  const handleEditProduct = async (productId, productData) => {
    await productService.updateProduct(productId, productData);
    await loadProducts();
  };

  const handleUpdateStock = async (productId, quantity) => {
    await productService.updateStock(productId, quantity);
    await loadProducts();
  };


  const handleDeleteProduct = async (product) => {
    if (!window.confirm(`¿Estás seguro de eliminar el producto "${product.name}"?`)) return;
    try {
      await productService.deleteProduct(product.product_id);
      await loadProducts();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Error al eliminar el producto';
      setError(errorMsg);
      alert(`Error: ${errorMsg}`);
    }
  };

  const handleExportExcel = () => {
    const exportParams = {};
    if (selectedCategory) exportParams.category_id = parseInt(selectedCategory);
    if (isActiveFilter === 'true') exportParams.is_active = true;
    if (isActiveFilter === 'false') exportParams.is_active = false;
    if (stockFilter) {
      const filterMap = { 'ok': 'in_stock', 'low': 'low_stock', 'out': 'out_of_stock', 'holds': 'with_holds' };
      exportParams.stock_filter = filterMap[stockFilter];
    }
    if (imageFilter !== '') exportParams.image = imageFilter === 'true';
    if (debouncedSearchName) exportParams.search = debouncedSearchName;
    if (debouncedSearchcodebar) exportParams.codebar_search = debouncedSearchcodebar;
    if (sortBy && sortBy !== 'relevance') exportParams.sort_by = sortBy;
    if (sortOrder) exportParams.sort_order = sortOrder;
    adminService.exportXLSX('productos', exportParams);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setDebouncedSearchName(searchName);
    setDebouncedSearchcodebar(searchcodebar);
  };

  if (!canViewCatalog) {
    return (
      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">Gestión de Inventario</h2>
        </div>
        <div className="empty-state" style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="empty-state__icon" style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</div>
          <h3 className="empty-state__title">Acceso Restringido</h3>
          <p className="empty-state__text">Tu rol no cuenta con el permiso 'catalog.view' para consultar el inventario de productos.</p>
        </div>
      </section>
    );
  }

  if (error && products.length === 0 && !loading) {
    return (
      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">Gestión de Inventario</h2>
        </div>
        <div className="empty-state">
          <p className="alert alert--danger">{error}</p>
          <button className="btn btn--primary btn--sm" onClick={() => { setError(null); loadProducts(); }}>
            Reintentar
          </button>
        </div>
      </section>
    );
  }

  const hasReservedStock = products.some(p => p.reserved_stock !== null && p.reserved_stock !== undefined);

  return (
    <section className="dashboard-section">
      <div className="section-header">
        <h2 className="section-title">Gestión de Inventario</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {canExport && (
            <button className="btn btn--secondary btn--sm" onClick={handleExportExcel} title="Exportar a Excel">
              <FontAwesomeIcon icon={faFileExport} /> Exportar Excel
            </button>
          )}
          {canManageProducts && (
            <button
              className="btn btn--primary btn--sm"
              onClick={() => { setShowEditModal(false); setShowStockModal(false); setSelectedProduct(null); setShowAddModal(true); }}
            >
              <FontAwesomeIcon icon={faPlus} /> Añadir Nuevo Producto
            </button>
          )}
        </div>
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      <div className="dashboard-controls">
        <form className="search-bar" onSubmit={handleSearch}>
          <input className="input" type="search" placeholder="Buscar por nombre, ID o descripción..." value={searchName} onChange={(e) => setSearchName(e.target.value)} />
          <button type="submit" className="btn btn--primary" aria-label="Buscar">
            <FontAwesomeIcon icon={faSearch} />
          </button>
        </form>

        <form className="search-bar" onSubmit={handleSearch}>
          <input className="input" type="search" placeholder="Buscar por codebar..." value={searchcodebar} onChange={(e) => setSearchcodebar(e.target.value)} />
          <button type="submit" className="btn btn--primary" aria-label="Buscar">
            <FontAwesomeIcon icon={faSearch} />
          </button>
        </form>

        <div className="filter-group">
          <label className="filter-group__label" htmlFor="filterCategory">Categoría:</label>
          <select className="select" id="filterCategory" value={selectedCategory} onChange={(e) => { setSelectedCategory(e.target.value); setPage(0); }}>
            <option value="">Todas</option>
            {categories.map(cat => (
              <option key={cat.category_id} value={cat.category_id}>{cat.name}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-group__label" htmlFor="filterStock">Stock:</label>
          <select className="select" id="filterStock" value={stockFilter} onChange={(e) => { setStockFilter(e.target.value); setPage(0); }}>
            <option value="">Todos</option>
            <option value="ok">En Stock</option>
            <option value="low">Bajo Stock</option>
            <option value="out">Agotado</option>
            <option value="holds">Con Apartados</option>
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-group__label" htmlFor="filterActive">Estado:</label>
          <select className="select" id="filterActive" value={isActiveFilter} onChange={(e) => { setIsActiveFilter(e.target.value); setPage(0); }}>
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
        </div>
        <div className="filter-group">
          <label className="filter-group__label" htmlFor="filterImage">Imagen:</label>
          <select className="select" id="filterImage" value={imageFilter} onChange={(e) => { setImageFilter(e.target.value); setPage(0); }}>
            <option value="">Todos</option>
            <option value="true">Con Imagen</option>
            <option value="false">Sin Imagen</option>
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-group__label" htmlFor="filterSort">Orden:</label>
          <select className="select" id="filterSort" value={`${sortBy}-${sortOrder}`} onChange={(e) => {
            const [field, order] = e.target.value.split('-');
            setSortBy(field);
            setSortOrder(order);
            setPage(0);
          }}>
            <option value="relevance-asc">Relevancia</option>
            <option value="created_at-desc">Más Recientes</option>
            <option value="name-asc">Nombre (A-Z)</option>
            <option value="name-desc">Nombre (Z-A)</option>
            <option value="price-asc">Precio (Menor a Mayor)</option>
            <option value="price-desc">Precio (Mayor a Menor)</option>
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Cargando productos..." />
      ) : (
        <div className="table-container">
          <table className="data-table data-table--inventory">
            <thead>
              <tr>
                <th>Img</th>
                <th>ID</th>
                <th>Producto</th>
                <th>Código de barras</th>
                <th>Categoría</th>
                <th>Ubicación</th>
                {canViewCost && <th>Precio Base</th>}
                <th>IVA</th>
                <th>Stock Actual</th>
                {hasReservedStock && <th>En Reserva</th>}
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr>
                  <td colSpan={(canViewCost ? 10 : 9) + (hasReservedStock ? 1 : 0)} className="text-center py-8">No se encontraron productos</td>
                </tr>
              ) : (
                products.map((product) => (
                  <ProductRow
                    key={product.product_id}
                    product={product}
                    onView={(p) => { setSelectedProduct(p); setShowViewModal(true); }}
                    onEdit={(p) => { setShowAddModal(false); setShowStockModal(false); setShowReservedStockModal(false); setSelectedProduct(p); setShowEditModal(true); }}
                    onDelete={handleDeleteProduct}
                    onUpdateStock={(p) => { setShowAddModal(false); setShowEditModal(false); setShowReservedStockModal(false); setSelectedProduct(p); setShowStockModal(true); }}
                    onUpdateReservedStock={(p) => { setShowAddModal(false); setShowEditModal(false); setShowStockModal(false); setSelectedProduct(p); setShowReservedStockModal(true); }}
                    onPreviewImage={(url, name) => setPreviewImage({ url, name })}
                    isAdmin={isAdmin}
                    canViewCost={canViewCost}
                    canUpdateStock={canUpdateStock}
                    canEdit={canEditProducts}
                    canDelete={canDeleteProducts}
                    showReservedStock={hasReservedStock}
                    canEditReservedStock={canEditReservedStock}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && (
        <ModalAddProduct isOpen={showAddModal} onClose={() => setShowAddModal(false)} onSubmit={handleAddProduct} />
      )}
      {showEditModal && (
        <ModalEditProduct isOpen={showEditModal} onClose={() => { setShowEditModal(false); setSelectedProduct(null); }} onSubmit={handleEditProduct} product={selectedProduct} />
      )}
      {showViewModal && (
        <ModalViewProduct isOpen={showViewModal} onClose={() => { setShowViewModal(true); setShowViewModal(false); setSelectedProduct(null); }} product={selectedProduct} />
      )}
      {showStockModal && (
        <ModalUpdateStock isOpen={showStockModal} onClose={() => { setShowStockModal(false); setSelectedProduct(null); }} onSubmit={handleUpdateStock} product={selectedProduct} />
      )}
      {showReservedStockModal && (
        <ModalProductStockHolds
          isOpen={showReservedStockModal}
          onClose={() => { setShowReservedStockModal(false); setSelectedProduct(null); }}
          product={selectedProduct}
          onHoldDeleted={() => loadProducts()}
          canDelete={canEditReservedStock}
        />
      )}

      {products.length > 0 && (
        <PaginationButtons
          currentPage={page}
          lookaheadPages={lookaheadPages}
          onPageChange={setPage}
        />
      )}

      {previewImage && (
        <div className="modal-overlay image-preview-overlay" onClick={() => setPreviewImage(null)}>
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3>{previewImage.name}</h3>
              <button className="modal__close" onClick={() => setPreviewImage(null)}>&times;</button>
            </div>
            <div className="modal__body">
              <div className="image-preview-box">
                <img 
                  className="image-preview-box__img"
                  src={previewImage.url} 
                  alt={previewImage.name} 
                  onError={(e) => { e.target.src = '/images/default-product.svg'; }}
                />
              </div>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setPreviewImage(null)}>Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}