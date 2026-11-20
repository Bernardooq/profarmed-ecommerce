import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faSearch, faSlidersH, faShoppingCart, faPlus, faMinus, 
  faCheck, faTrash, faArrowRight, faDownload, faBoxes, faBarcode, faBroom,
  faExclamationTriangle, faCheckCircle, faTimes, faChevronLeft, faChevronRight
} from '@fortawesome/free-solid-svg-icons';
import { useCart } from '../../context/CartContext';
import { useNavigate } from 'react-router-dom';
import { formatCurrency } from '../../utils/formatUtils';

export default function PosCatalogView({
  products,
  loading,
  categories,
  selectedCategory,
  setSelectedCategory,
  sortOrder,
  onSortChange,
  searchQuery,
  onSearchChange,
  onProductClick,
  isColumnVisible,
  openColumnPicker,
  onExportCatalog
}) {
  const navigate = useNavigate();
  const { items: cartItems, addToCart, updateQuantity, removeItem, clearCart, total } = useCart();

  const [quantities, setQuantities] = useState({});
  const [addingId, setAddingId] = useState(null);
  const [localSearch, setLocalSearch] = useState(searchQuery || '');
  const [clearingCart, setClearingCart] = useState(false);
  const [toast, setToast] = useState(null);
  const [isCartOpen, setIsCartOpen] = useState(false);

  const showToast = (message, isWarning = false) => {
    setToast({ message, isWarning });
    setTimeout(() => setToast(null), 3500);
  };

  const getQty = (productId) => {
    const val = quantities[productId];
    return val !== undefined ? val : 1;
  };

  const setQty = (productId, val, maxStock = 9999) => {
    if (val === '') {
      setQuantities(prev => ({ ...prev, [productId]: '' }));
      return;
    }
    const parsed = parseInt(val, 10);
    if (isNaN(parsed) || parsed < 1) {
      setQuantities(prev => ({ ...prev, [productId]: 1 }));
    } else if (parsed > maxStock) {
      setQuantities(prev => ({ ...prev, [productId]: maxStock }));
      showToast(`Cantidad ajustada al stock disponible (${maxStock} unidades)`, true);
    } else {
      setQuantities(prev => ({ ...prev, [productId]: parsed }));
    }
  };

  const handleBlur = (productId, maxStock = 9999) => {
    const rawVal = quantities[productId];
    const current = parseInt(rawVal, 10);
    if (isNaN(current) || current < 1) {
      setQuantities(prev => ({ ...prev, [productId]: 1 }));
    } else if (current > maxStock) {
      setQuantities(prev => ({ ...prev, [productId]: maxStock }));
      showToast(`Cantidad limitada al máximo stock disponible (${maxStock})`, true);
    }
  };

  const handleAdd = async (product) => {
    const rawQty = quantities[product.product_id];
    const qtyToAdd = Math.max(1, parseInt(rawQty, 10) || 1);

    // Asegurar que en el input no quede vacío tras agregar
    setQuantities(prev => ({ ...prev, [product.product_id]: qtyToAdd }));

    try {
      setAddingId(product.product_id);
      await addToCart(product.product_id, qtyToAdd);
      showToast(`¡Se agregó ${qtyToAdd}x "${product.name}" al carrito!`, false);
    } catch (err) {
      showToast(err.message || 'Error agregando al carrito', true);
    } finally {
      setAddingId(null);
    }
  };

  const handleRemove = async (cartId) => {
    try {
      await removeItem(cartId);
      showToast('Producto eliminado del carrito', false);
    } catch (err) {
      showToast(err.message || 'Error eliminando el producto del carrito', true);
    }
  };

  const handleClearCart = async () => {
    if (!window.confirm('¿Estás seguro de que deseas vaciar todos los productos del carrito?')) return;
    try {
      setClearingCart(true);
      await clearCart();
      showToast('Carrito vaciado completamente', false);
    } catch (err) {
      showToast(err.message || 'Error al vaciar el carrito', true);
    } finally {
      setClearingCart(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (onSearchChange) {
      onSearchChange(localSearch);
    }
  };

  const cartMap = {};
  cartItems.forEach(ci => {
    if (ci.product?.product_id) {
      cartMap[ci.product.product_id] = ci;
    }
  });

  const activeTotal = total && total > 0 
    ? total 
    : cartItems.reduce((sum, item) => {
        const p = item.product || {};
        const price = item.final_price ?? item.price_at_addition ?? p.final_price ?? p.base_price ?? p.price ?? 0;
        return sum + (price * (item.quantity || 0));
      }, 0);

  return (
    <div className="pos-container" style={{ position: 'relative' }}>
      {/* TOAST DE NOTIFICACIÓN FLOTANTE */}
      {toast && (
        <div 
          className={`toast-notification ${toast.isWarning ? 'toast-warning' : 'toast-success'}`}
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            backgroundColor: toast.isWarning ? '#fef3c7' : '#dcfce7',
            color: toast.isWarning ? '#92400e' : '#166534',
            border: `1px solid ${toast.isWarning ? '#f59e0b' : '#22c55e'}`,
            padding: '12px 18px',
            borderRadius: '10px',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontWeight: 600,
            fontSize: '13px',
            animation: 'fadeIn 0.2s ease'
          }}
        >
          <FontAwesomeIcon icon={toast.isWarning ? faExclamationTriangle : faCheckCircle} size="lg" />
          <span>{toast.message}</span>
        </div>
      )}

      {/* TOOLBAR SUPERIOR DEL PUNTO DE VENTA */}
      <div className="pos-toolbar">
        <form className="pos-search-form" onSubmit={handleSearchSubmit}>
          <div className="pos-input-group">
            <FontAwesomeIcon icon={faSearch} className="pos-search-icon" />
            <input
              type="text"
              placeholder="Buscar por nombre, código de barras, marca o fórmula..."
              value={localSearch}
              onChange={e => setLocalSearch(e.target.value)}
            />
            {localSearch && (
              <button type="button" className="btn-clear" onClick={() => { setLocalSearch(''); onSearchChange(''); }}>
                ×
              </button>
            )}
          </div>
          <button type="submit" className="btn btn--primary btn--sm">Buscar</button>
        </form>

        <div className="pos-toolbar-actions">
          {/* FILTRO DE CATEGORÍA */}
          <select 
            className="pos-select" 
            value={selectedCategory} 
            onChange={e => setSelectedCategory(e.target.value)}
          >
            <option value="">Todas las Categorías</option>
            {categories.map(c => (
              <option key={c.category_id} value={c.category_id}>{c.name}</option>
            ))}
          </select>

          {/* SELECTOR DE ORDENAMIENTO */}
          {onSortChange && (
            <select
              className="pos-select"
              value={sortOrder || 'relevance'}
              onChange={e => onSortChange(e.target.value)}
              title="Ordenar catálogo"
            >
              <option value="relevance">Relevancia</option>
              <option value="newest">Más Recientes</option>
              <option value="price_asc">Precio: Menor a Mayor</option>
              <option value="price_desc">Precio: Mayor a Menor</option>
              <option value="name_asc">Nombre: A-Z</option>
              <option value="name_desc">Nombre: Z-A</option>
            </select>
          )}

          <button className="btn btn--secondary btn--sm" onClick={openColumnPicker} title="Configurar columnas">
            <FontAwesomeIcon icon={faSlidersH} style={{ marginRight: '6px' }} />
            Columnas
          </button>

          <button
            type="button"
            className={`btn btn--sm pos-cart-toggle ${isCartOpen ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => setIsCartOpen(prev => !prev)}
            title={isCartOpen ? 'Ocultar carrito lateral' : 'Mostrar carrito lateral'}
          >
            <FontAwesomeIcon icon={faShoppingCart} />
            <span>Carrito ({cartItems.length})</span>
            {cartItems.length > 0 && !isCartOpen && (
              <span className="pos-cart-toggle__total">{formatCurrency(activeTotal)}</span>
            )}
            <FontAwesomeIcon icon={isCartOpen ? faChevronRight : faChevronLeft} size="xs" />
          </button>
        </div>
      </div>

      {/* ÁREA PRINCIPAL: TABLA 100% O DIVIDIDA CON CARRITO LATERAL */}
      <div className={`pos-content ${isCartOpen ? 'pos-content--cart-open' : ''}`}>
        {/* TABLA DE PRODUCTOS (REUTILIZA data-table NATIVO) */}
        <div className="pos-table-wrapper data-table">
          <table className="pos-table">
            <thead>
              <tr>
                {isColumnVisible('img') && <th style={{ width: '60px' }}>Imagen</th>}
                {isColumnVisible('codebar') && <th style={{ width: '140px' }}>Cód. Barras</th>}
                {isColumnVisible('name') && <th>Producto</th>}
                {isColumnVisible('category') && <th>Categoría</th>}
                {isColumnVisible('unit') && <th style={{ width: '90px' }}>Unidad</th>}
                {isColumnVisible('description') && <th>Detalle</th>}
                {isColumnVisible('stock') && <th style={{ width: '90px', textAlign: 'center' }}>Stock</th>}
                {isColumnVisible('price') && <th style={{ width: '110px', textAlign: 'right' }}>Precio</th>}
                {isColumnVisible('actions') && <th style={{ width: '210px', textAlign: 'center' }}>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="12" className="pos-empty">Cargando productos...</td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan="12" className="pos-empty">No se encontraron productos en el catálogo.</td>
                </tr>
              ) : (
                products.map(p => {
                  const inCartItem = cartMap[p.product_id];
                  const inCartQty = inCartItem?.quantity || 0;
                  const stock = p.stock_count || 0;
                  const isOutOfStock = stock <= 0;
                  const currentQty = getQty(p.product_id);
                  const numQty = parseInt(currentQty, 10) || 1;
                  const displayPrice = p.final_price ?? p.base_price ?? p.price ?? 0;

                  return (
                    <tr key={p.product_id} className={inCartQty > 0 ? 'row-in-cart' : ''}>
                      {/* IMAGEN */}
                      {isColumnVisible('img') && (
                        <td className="col-img">
                          {p.image_url ? (
                            <img 
                              src={p.image_url} 
                              alt={p.name} 
                              className="pos-thumb"
                              onClick={() => onProductClick && onProductClick(p)}
                            />
                          ) : (
                            <div className="pos-thumb-placeholder">
                              <FontAwesomeIcon icon={faBoxes} size="xs" />
                            </div>
                          )}
                        </td>
                      )}

                      {/* CÓDIGO DE BARRAS EAN */}
                      {isColumnVisible('codebar') && (
                        <td className="col-codebar">
                          {p.codebar ? (
                            <span title={p.codebar} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                              <FontAwesomeIcon icon={faBarcode} style={{ marginRight: '4px', opacity: 0.7 }} />
                              {p.codebar}
                            </span>
                          ) : (
                            <span className="text-muted">-</span>
                          )}
                        </td>
                      )}

                      {/* NOMBRE */}
                      {isColumnVisible('name') && (
                        <td className="col-name">
                          <span 
                            className="product-title-link" 
                            onClick={() => onProductClick && onProductClick(p)}
                          >
                            {p.name}
                          </span>
                          {p.has_discount && (
                            <span className="badge badge--discount badge--sm">
                              Promo -{p.discount_applied}%
                            </span>
                          )}
                          {inCartQty > 0 && (
                            <span className="badge-in-cart">
                              <FontAwesomeIcon icon={faCheck} size="xs" /> En Carrito ({inCartQty})
                            </span>
                          )}
                        </td>
                      )}

                      {/* CATEGORÍA */}
                      {isColumnVisible('category') && (
                        <td className="col-category">
                          <span className="badge-category">{p.category?.name || 'General'}</span>
                        </td>
                      )}

                      {/* UNIDAD DE MEDIDA */}
                      {isColumnVisible('unit') && (
                        <td className="col-unit">
                          <span className="badge-category">{p.unidad_medida || 'Pza'}</span>
                        </td>
                      )}

                      {/* DESCRIPCIÓN / FÓRMULA / DETALLE */}
                      {isColumnVisible('description') && (
                        <td className="col-description">
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                            {p.description && (
                              <span className="text-sm" style={{ fontWeight: 500, color: 'var(--color-text)' }}>
                                {p.description}
                              </span>
                            )}
                            {p.descripcion_2 && (
                              <span className="text-muted text-xs">
                                {p.descripcion_2}
                              </span>
                            )}
                            {!p.description && !p.descripcion_2 && (
                              <span className="text-muted text-sm">-</span>
                            )}
                          </div>
                        </td>
                      )}

                      {/* STOCK */}
                      {isColumnVisible('stock') && (
                        <td className="col-stock" style={{ textAlign: 'center' }}>
                          {isOutOfStock ? (
                            <span className="badge-stock badge-stock--out">Agotado</span>
                          ) : (
                            <span className="badge-stock badge-stock--available">{stock}</span>
                          )}
                        </td>
                      )}

                      {/* PRECIO */}
                      {isColumnVisible('price') && (
                        <td className="col-price" style={{ textAlign: 'right' }}>
                          {p.has_discount && p.original_price && (
                            <div className="price-strike price-strike--sm">
                              {formatCurrency(p.original_price)}
                            </div>
                          )}
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                            <span className="pos-price">{formatCurrency(displayPrice)}</span>
                            {p.has_discount && (
                              <span className="badge badge--discount badge--sm">
                                -{p.discount_applied}%
                              </span>
                            )}
                          </div>
                        </td>
                      )}

                      {/* ACCIONES DE CANTIDAD Y AGREGAR */}
                      {isColumnVisible('actions') && (
                        <td className="col-actions" style={{ textAlign: 'center' }}>
                          <div className="pos-qty-controls">
                            <button
                              type="button"
                              className="btn-qty"
                              disabled={isOutOfStock || numQty <= 1}
                              onClick={() => setQty(p.product_id, numQty - 1, stock)}
                            >
                              <FontAwesomeIcon icon={faMinus} size="xs" />
                            </button>

                            <input
                              type="number"
                              className="input-qty"
                              min="1"
                              max={stock || 1}
                              disabled={isOutOfStock}
                              value={currentQty}
                              onChange={e => setQty(p.product_id, e.target.value, stock)}
                              onBlur={() => handleBlur(p.product_id, stock)}
                            />

                            <button
                              type="button"
                              className="btn-qty"
                              disabled={isOutOfStock || numQty >= stock}
                              onClick={() => setQty(p.product_id, numQty + 1, stock)}
                            >
                              <FontAwesomeIcon icon={faPlus} size="xs" />
                            </button>

                            <button
                              type="button"
                              className="btn btn--primary btn--xs btn-add-pos"
                              disabled={isOutOfStock || addingId === p.product_id}
                              onClick={() => handleAdd(p)}
                            >
                              {addingId === p.product_id ? 'Wait...' : 'Agregar'}
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* CARRITO LATERAL COLAPSABLE / DRAWER RESPONSIVE */}
        {isCartOpen && (
          <>
            <div className="pos-cart-backdrop" onClick={() => setIsCartOpen(false)} />
            <div className="pos-side-cart">
              <div className="pos-side-cart-header">
                <h4>
                  <FontAwesomeIcon icon={faShoppingCart} style={{ marginRight: '8px', color: 'var(--color-primary)' }} />
                  Carrito ({cartItems.length})
                </h4>

                <div className="pos-side-cart-header__actions">
                  {cartItems.length > 0 && (
                    <button 
                      type="button"
                      className="btn btn--ghost btn--xs text-danger"
                      style={{ fontSize: '11px', padding: '2px 6px' }}
                      onClick={handleClearCart}
                      disabled={clearingCart}
                      title="Vaciar carrito completo"
                    >
                      <FontAwesomeIcon icon={faBroom} style={{ marginRight: '4px' }} />
                      Vaciar
                    </button>
                  )}
                  <button
                    type="button"
                    className="pos-side-cart-close"
                    onClick={() => setIsCartOpen(false)}
                    title="Ocultar carrito"
                    aria-label="Ocultar carrito"
                  >
                    <FontAwesomeIcon icon={faTimes} />
                  </button>
                </div>
              </div>

          <div className="pos-side-cart-body">
            {cartItems.length === 0 ? (
              <div className="cart-empty-state">
                <FontAwesomeIcon icon={faShoppingCart} size="2x" style={{ opacity: 0.2, marginBottom: '8px' }} />
                <p>El carrito está vacío.</p>
                <small className="text-muted">Agrega productos desde la tabla para cotizar y pedir al instante.</small>
              </div>
            ) : (
              <ul className="cart-items-list">
                {cartItems.map(item => {
                  const p = item.product || {};
                  const price = item.final_price ?? item.price_at_addition ?? p.final_price ?? p.base_price ?? p.price ?? 0;
                  const subtotal = price * item.quantity;
                  const targetCartId = item.cart_cache_id || item.cart_id;

                  return (
                    <li key={targetCartId} className="cart-item-row">
                      <div className="cart-item-info">
                        <span className="cart-item-title">{p.name || `Producto ${item.product_id}`}</span>
                        <span className="cart-item-meta">{formatCurrency(price)} c/u</span>
                      </div>

                      <div className="cart-item-actions">
                        <div className="mini-qty-box">
                          <button 
                            type="button" 
                            onClick={() => updateQuantity(targetCartId, item.quantity - 1)}
                            disabled={item.quantity <= 1}
                          >
                            -
                          </button>
                          <span>{item.quantity}</span>
                          <button 
                            type="button" 
                            onClick={() => updateQuantity(targetCartId, item.quantity + 1)}
                          >
                            +
                          </button>
                        </div>

                        <span className="cart-item-subtotal">{formatCurrency(subtotal)}</span>

                        <button 
                          type="button" 
                          className="btn-remove-item"
                          onClick={() => handleRemove(targetCartId)}
                          title="Eliminar producto"
                        >
                          <FontAwesomeIcon icon={faTrash} size="xs" />
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {cartItems.length > 0 && (
            <div className="pos-side-cart-footer">
              <div className="cart-total-row">
                <span>Total:</span>
                <span className="cart-total-amount">{formatCurrency(activeTotal)}</span>
              </div>
              <button 
                className="btn btn--primary btn--block btn--sm" 
                onClick={() => navigate('/cart')}
              >
                Procesar Pedido
                <FontAwesomeIcon icon={faArrowRight} style={{ marginLeft: '8px' }} />
              </button>
            </div>
          )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
