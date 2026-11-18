import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faPlus, faTrashAlt, faPencilAlt, faCheck, faTimes, faLock, faBox, faInfoCircle } from '@fortawesome/free-solid-svg-icons';
import priceListService from '../../../services/priceListService';
import LoadingSpinner from '../../common/LoadingSpinner';
import ErrorMessage from '../../common/ErrorMessage';
import { formatCurrency, formatNumber } from '../../../utils/formatUtils';
import PaginationButtons from '../../common/PaginationButtons';
import { getProductImageUrl } from '../../../utils/imageUtils';
import { usePaginationLimit } from '../../../context/PaginationLimitContext';
import { usePermissions } from '../../../hooks/usePermissions';
import { PERMISSIONS } from '../../../config/permissions';

export default function ModalPriceListItems({ isOpen, onClose, priceList }) {
  const { can, isAdmin } = usePermissions();
  const canManagePrices = isAdmin || can(PERMISSIONS.CATALOG_PRICES);
  const [availableProducts, setAvailableProducts] = useState([]);
  const [availableLoading, setAvailableLoading] = useState(false);
  const [availableSearch, setAvailableSearch] = useState('');
  const [availablePage, setAvailablePage] = useState(0);
  const [availableListPage, setAvailableListPage] = useState(0);
  const [availableHasMore, setAvailableHasMore] = useState(true);
  const [availableListHasMore, setAvailableListHasMore] = useState(true);

  const [listItems, setListItems] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const [listSearch, setListSearch] = useState('');

  const [debouncedAvailableSearch, setDebouncedAvailableSearch] = useState('');
  const [debouncedListSearch, setDebouncedListSearch] = useState('');

  const [error, setError] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [editMarkup, setEditMarkup] = useState('');
  const [newItemMarkup, setNewItemMarkup] = useState({});

  const { limit: itemsPerPage } = usePaginationLimit();

  // Debounce effects for typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedAvailableSearch(availableSearch);
      setAvailablePage(0);
    }, 2500);
    return () => clearTimeout(timer);
  }, [availableSearch]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedListSearch(listSearch);
      setAvailableListPage(0);
    }, 2500);
    return () => clearTimeout(timer);
  }, [listSearch]);

  // Immediate handlers for Search Buttons / Enter
  const handleAvailableSearch = (e) => {
    if (e) e.preventDefault();
    setDebouncedAvailableSearch(availableSearch);
    setAvailablePage(0);
  };

  const handleListSearch = (e) => {
    if (e) e.preventDefault();
    setDebouncedListSearch(listSearch);
    setAvailableListPage(0);
  };

  useEffect(() => {
    if (isOpen && priceList) {
      loadListItems();
      if (canManagePrices) {
        loadAvailableProducts();
      }
    }
  }, [isOpen, priceList, itemsPerPage, canManagePrices]);

  useEffect(() => {
    if (isOpen && priceList && canManagePrices) {
      loadAvailableProducts();
    }
  }, [availablePage, debouncedAvailableSearch, itemsPerPage, canManagePrices]);

  useEffect(() => {
    if (isOpen && priceList) {
      loadListItems();
    }
  }, [availableListPage, debouncedListSearch, itemsPerPage]);

  const loadListItems = async () => {
    const params = { skip: availableListPage * itemsPerPage, limit: itemsPerPage + 1, search: debouncedListSearch || undefined };
    try {
      setListLoading(true); setError(null); const items = await priceListService.getItemsWithDetails(priceList.price_list_id, params);
      const hasMore = items.length > itemsPerPage; setAvailableListHasMore(hasMore); setListItems(hasMore ? items.slice(0, itemsPerPage) : items);
    } catch (err) { setError('Error al cargar los productos de la lista'); console.error(err); }
    finally { setListLoading(false); }
  };

  const loadAvailableProducts = async () => {
    try {
      setAvailableLoading(true); const products = await priceListService.getAvailableProducts(priceList.price_list_id, { limit: itemsPerPage + 1, skip: availablePage * itemsPerPage, search: debouncedAvailableSearch || undefined });
      const hasMore = products.length > itemsPerPage; setAvailableHasMore(hasMore); setAvailableProducts(hasMore ? products.slice(0, itemsPerPage) : products);
    } catch (err) { console.error(err); }
    finally { setAvailableLoading(false); }
  };

  const handleAddProduct = async (product) => {
    const markup = newItemMarkup[product.product_id] || '30.00';
    try {
      setError(null); await priceListService.createPriceListItem(priceList.price_list_id, { product_id: product.product_id, markup_percentage: parseFloat(markup) });
      loadListItems(); loadAvailableProducts();
      setNewItemMarkup(prev => { const updated = { ...prev }; delete updated[product.product_id]; return updated; });
    } catch (err) { setError(err.message || 'Error al añadir el producto'); }
  };

  const handleRemoveProduct = async (productId) => {
    if (!window.confirm('¿Estás seguro de eliminar este producto de la lista?')) return;
    try { setError(null); await priceListService.deletePriceListItem(priceList.price_list_id, productId); loadListItems(); loadAvailableProducts(); }
    catch (err) { setError(err.message || 'Error al eliminar el producto'); }
  };

  const startEdit = (item) => { setEditingItem(item.product?.product_id); setEditMarkup(item.markup_percentage.toString()); };
  const cancelEdit = () => { setEditingItem(null); setEditMarkup(''); };
  const saveEdit = async (productId) => {
    try { setError(null); await priceListService.updatePriceListItem(priceList.price_list_id, productId, { markup_percentage: parseFloat(editMarkup) }); await loadListItems(); setEditingItem(null); setEditMarkup(''); }
    catch (err) { setError(err.message || 'Error al actualizar el markup'); }
  };

  if (!isOpen || !priceList) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--xl" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div>
            <div className="d-flex align-items-center gap-2 flex-wrap">
              <h2 className="m-0">
                {canManagePrices ? 'Gestionar Productos' : 'Consulta de Precios Autorizados'}: {priceList.list_name}
              </h2>
              {!canManagePrices && (
                <span className="badge badge--info" title="Costos base de proveedor y márgenes ERP confidenciales y protegidos">
                  <FontAwesomeIcon icon={faLock} className="me-1" /> Precios Autorizados al Cliente
                </span>
              )}
            </div>
            {priceList.description ? (
              <p className="text-muted mt-1 mb-0">{priceList.description}</p>
            ) : (
              <p className="text-muted text-sm mt-1 mb-0">
                {canManagePrices 
                  ? 'Asignación de márgenes comerciales y catálogo por lista.'
                  : 'Precios finales autorizados con impuestos incluidos para cotización y venta.'}
              </p>
            )}
          </div>
          <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">×</button>
        </div>
        <div className="modal__body">
          {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

          {!canManagePrices ? (
            /* READ-ONLY VIEW (Para roles con solo permiso público interno, ej. seller) */
            <div className="single-view">
              <div className="single-view__toolbar">
                <div className="single-view__info">
                  <FontAwesomeIcon icon={faInfoCircle} className="text-primary" />
                  <span>
                    <strong>Catálogo Comercial:</strong> Precios autorizados para cotizaciones y venta. Para agregar nuevos productos o modificar márgenes, solicita la gestión a un Administrador.
                  </span>
                </div>
                <form className="search-bar search-bar--sm single-view__search" onSubmit={handleListSearch}>
                  <input 
                    className="input" 
                    type="search" 
                    placeholder="Buscar por producto, SKU o código..." 
                    value={listSearch} 
                    onChange={(e) => { setListSearch(e.target.value); }} 
                  />
                  <button className="btn btn--primary" type="submit" aria-label="Buscar"><FontAwesomeIcon icon={faSearch} /></button>
                </form>
              </div>

              <div className="split-view__list-container single-view__list-container">
                {listLoading ? <LoadingSpinner message="Cargando productos..." /> : listItems.length === 0 ? (
                  <p className="empty-state text-center py-5">{listSearch ? 'No se encontraron productos con esa búsqueda' : 'No hay productos en esta lista'}</p>
                ) : (
                  <div className="single-view__list">
                    {listItems.map(item => {
                      const product = item.product || {};
                      const ivaPercentage = parseFloat(item.iva_percentage || product.iva_percentage || 0);
                      const finalPrice = item.final_price;
                      const stock = product.stock_count;

                      return (
                        <div key={product.product_id} className="product-card product-card--read-only">
                          <div className="product-card__main-content">
                            <div className="product-card__thumbnail-wrapper">
                              <img 
                                src={getProductImageUrl(product)} 
                                alt="" 
                                className="product-card__thumbnail"
                                onError={(e) => { 
                                  e.target.onerror = null;
                                  e.target.src = '/images/default-product.svg'; 
                                }}
                              />
                            </div>
                            <div className="product-card__info">
                              <div className="product-card__name" title={product.name}>
                                {product.name}
                              </div>
                              <div className="product-card__meta-tags">
                                <span><strong>SKU:</strong> {product.product_id}</span>
                                {product.codebar && <span>| <strong>CB:</strong> {product.codebar}</span>}
                                {product.unidad_medida && <span>| <strong>Presentación:</strong> {product.unidad_medida}</span>}
                                {stock !== undefined && stock !== null && (
                                  <span className={`badge ${stock > 0 ? 'badge--success' : 'badge--secondary'}`}>
                                    <FontAwesomeIcon icon={faBox} className="me-1" /> {stock > 0 ? `${stock} disp.` : 'Sin existencias'}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="product-card__price-section">
                            <span className="text-xs text-muted">IVA: {ivaPercentage.toFixed(0)}%</span>
                            <span className="product-card__final-price">
                              {formatCurrency(finalPrice)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
              <PaginationButtons onPrev={() => setAvailableListPage(p => Math.max(0, p - 1))} onNext={() => setAvailableListPage(p => p + 1)} canGoPrev={availableListPage > 0} canGoNext={availableListHasMore} />
            </div>
          ) : (
            /* FULL MANAGEMENT VIEW (Para administradores de precios con catalog.prices) */
            <div className="split-view">
              {/* LEFT: Available Products */}
              <div className="split-view__column">
                <h3>Productos Disponibles</h3>
                <form className="search-bar search-bar--sm" onSubmit={handleAvailableSearch}>
                  <input className="input" type="search" placeholder="Buscar producto..." value={availableSearch} onChange={(e) => { setAvailableSearch(e.target.value); }} />
                  <button className="btn btn--primary" type="submit" aria-label="Buscar"><FontAwesomeIcon icon={faSearch} /></button>
                </form>
                <div className="split-view__list-container">
                  {availableLoading ? <LoadingSpinner message="Cargando..." /> : availableProducts.length === 0 ? (
                    <p className="empty-state">{availableSearch ? 'No se encontraron productos' : 'Todos los productos están en la lista'}</p>
                  ) : (
                    <div className="split-view__list">
                      {availableProducts.map(product => (
                        <div key={product.product_id} className="product-card">
                          <div className="product-card__row">
                            <img 
                              src={getProductImageUrl(product)} 
                              alt="" 
                              className="product-card__thumbnail"
                              onError={(e) => { 
                                e.target.onerror = null;
                                e.target.src = '/images/default-product.svg'; 
                              }}
                            />
                            <div className="product-card__info product-card__info-row">
                              <div className="product-card__name">{product.name}</div>
                              <div className="product-card__meta">Codigo de barras: {product.codebar}</div>
                              <div className="product-card__price">Precio Base: {formatCurrency(product.base_price)}</div>
                            </div>
                          </div>
                          {canManagePrices && (
                            <div className="product-card__actions justify-between">
                              <input className="input input--sm input--markup" type="number" placeholder="Markup %" value={newItemMarkup[product.product_id] || ''} onChange={(e) => setNewItemMarkup(prev => ({ ...prev, [product.product_id]: e.target.value }))} step="0.01" min="0" />
                              <button className="btn btn--icon btn--success" onClick={() => handleAddProduct(product)} title="Añadir a la lista">
                                <FontAwesomeIcon icon={faPlus} />
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <PaginationButtons onPrev={() => setAvailablePage(p => Math.max(0, p - 1))} onNext={() => setAvailablePage(p => p + 1)} canGoPrev={availablePage > 0} canGoNext={availableHasMore} />
              </div>

              {/* RIGHT: Products in List */}
              <div className="split-view__column">
                <h3>Productos en la Lista</h3>
                <form className="search-bar search-bar--sm" onSubmit={handleListSearch}>
                  <input className="input" type="search" placeholder="Buscar en la lista..." value={listSearch} onChange={(e) => { setListSearch(e.target.value); }} />
                  <button className="btn btn--primary" type="submit" aria-label="Buscar"><FontAwesomeIcon icon={faSearch} /></button>
                </form>
                <div className="split-view__list-container">
                  {listLoading ? <LoadingSpinner message="Cargando..." /> : listItems.length === 0 ? (
                    <p className="empty-state">{listSearch ? 'No se encontraron productos con esa búsqueda' : 'No hay productos en esta lista'}</p>
                  ) : (
                    <div className="split-view__list">
                      {listItems.map(item => {
                        const isEditing = editingItem === item.product?.product_id;
                        const markup = isEditing ? parseFloat(editMarkup) : (item.markup_percentage || 0);
                        const basePrice = parseFloat(item.product?.base_price || 0);
                        const ivaPercentage = parseFloat(item.product?.iva_percentage || 0);
                        let priceWithoutIva, markupAmount, ivaAmount, finalPriceWithIva;
                        if (isEditing) {
                          markupAmount = basePrice * (markup / 100);
                          priceWithoutIva = basePrice + markupAmount;
                          ivaAmount = priceWithoutIva * (ivaPercentage / 100);
                          finalPriceWithIva = priceWithoutIva + ivaAmount;
                        } else {
                          finalPriceWithIva = item.final_price != null ? parseFloat(item.final_price) : 0;
                          priceWithoutIva = item.price_with_markup != null ? parseFloat(item.price_with_markup) : (finalPriceWithIva / (1 + ivaPercentage / 100));
                          markupAmount = item.markup_amount != null ? parseFloat(item.markup_amount) : Math.max(0, priceWithoutIva - basePrice);
                          ivaAmount = Math.max(0, finalPriceWithIva - priceWithoutIva);
                        }

                        return (
                          <div key={item.product?.product_id} className="product-card product-card--in-list">
                            <div className="product-card__row">
                              <img 
                                src={getProductImageUrl(item.product)} 
                                alt="" 
                                className="product-card__thumbnail"
                                onError={(e) => { 
                                  e.target.onerror = null;
                                  e.target.src = '/images/default-product.svg'; 
                                }}
                              />
                              <div className="product-card__info product-card__info-row">
                                <div className="product-card__name">{item.product?.name}</div>
                                <div className="product-card__meta">Codigo de barras: {item.product?.codebar}</div>
                                <div className="product-card__price text-sm">Base: {formatCurrency(basePrice)}</div>
                                <div className="product-card__meta my-1">
                                  {isEditing ? (
                                    <input className="input input--sm input--markup" type="number" value={editMarkup} onChange={(e) => setEditMarkup(e.target.value)} step="0.01" min="0" autoFocus />
                                  ) : (
                                    <span>Markup: {formatNumber(markup)}% ({formatCurrency(markupAmount)})</span>
                                  )}
                                </div>
                                <div className="product-card__meta">IVA: {ivaPercentage.toFixed(0)}% ({formatCurrency(ivaAmount)})</div>
                                <div className="product-card__price"><strong>Final: {formatCurrency(finalPriceWithIva)}</strong></div>
                              </div>
                            </div>
                            <div className="product-card__actions justify-end">
                              {canManagePrices && (
                                isEditing ? (
                                  <>
                                    <button className="btn btn--icon btn--success" onClick={() => saveEdit(item.product?.product_id)} title="Guardar"><FontAwesomeIcon icon={faCheck} /></button>
                                    <button className="btn btn--icon btn--secondary" onClick={cancelEdit} title="Cancelar"><FontAwesomeIcon icon={faTimes} /></button>
                                  </>
                                ) : (
                                  <>
                                    <button className="btn btn--icon btn--ghost" onClick={() => startEdit(item)} title="Editar markup"><FontAwesomeIcon icon={faPencilAlt} /></button>
                                    <button className="btn btn--icon btn--danger" onClick={() => handleRemoveProduct(item.product?.product_id)} title="Eliminar de la lista"><FontAwesomeIcon icon={faTrashAlt} /></button>
                                  </>
                                )
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
                <PaginationButtons onPrev={() => setAvailableListPage(p => Math.max(0, p - 1))} onNext={() => setAvailableListPage(p => p + 1)} canGoPrev={availableListPage > 0} canGoNext={availableListHasMore} />
              </div>
            </div>
          )}
        </div>
        <div className="modal__footer">
          <button type="button" className="btn btn--primary" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}