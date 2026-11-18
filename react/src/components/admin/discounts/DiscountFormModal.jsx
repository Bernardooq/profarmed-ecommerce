import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTag, faPercentage } from '@fortawesome/free-solid-svg-icons';

export default function DiscountFormModal({
  isOpen,
  onClose,
  editingDiscount,
  formData,
  setFormData,
  formSubmitting,
  formError,
  handleFormSubmit,
  selectedProduct,
  setSelectedProduct,
  productSearch,
  setProductSearch,
  searchingProducts,
  productSearchResults,
  setProductSearchResults,
  priceLists
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay discounts-manager__modal-overlay" onClick={onClose}>
      <div className="modal modal--md discounts-manager__modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header discounts-manager__modal-header">
          <h3 className="d-flex align-items-center gap-2">
            <FontAwesomeIcon icon={faTag} className="text-primary" />
            {editingDiscount ? 'Editar Descuento' : 'Nuevo Descuento / Promoción'}
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>
            &times;
          </button>
        </div>

        <form onSubmit={handleFormSubmit} className="discounts-manager__modal-form">
          <div className="modal__body discounts-manager__modal-body">
            {formError && (
              <div className="discounts-manager__alert-danger">
                {formError}
              </div>
            )}

            {/* Selección de Producto */}
            <div>
              <label className="label discounts-manager__field-label">Producto *</label>
              {selectedProduct ? (
                <div className="discounts-manager__selected-box">
                  <div>
                    <div className="discounts-manager__product-id">{selectedProduct.product_id}</div>
                    <div className="discounts-manager__product-name">{selectedProduct.name}</div>
                  </div>
                  {!editingDiscount && (
                    <button type="button" className="btn btn--sm btn--ghost" onClick={() => setSelectedProduct(null)}>
                      Cambiar
                    </button>
                  )}
                </div>
              ) : (
                <div>
                  <input
                    type="text"
                    className="input"
                    placeholder="Escribe para buscar producto por código o nombre..."
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                  />
                  {searchingProducts && <div className="text-muted text-xs mt-1">Buscando...</div>}
                  {productSearchResults.length > 0 && (
                    <ul className="discounts-manager__search-dropdown">
                      {productSearchResults.map(p => (
                        <li
                          key={p.product_id}
                          onClick={() => { setSelectedProduct(p); setProductSearchResults([]); }}
                          className="discounts-manager__search-item"
                        >
                          <span><strong>{p.product_id}</strong> - {p.name}</span>
                          <span>${p.final_price || p.base_price}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Tipo de Ámbito */}
            <div>
              <label className="label discounts-manager__field-label">Tipo de Descuento (Ámbito) *</label>
              <div className="discounts-manager__scope-grid">
                <label className={`discounts-manager__scope-card ${formData.scope_type === 'general' ? 'discounts-manager__scope-card--active' : ''}`}>
                  <input
                    type="radio"
                    name="scope_type"
                    value="general"
                    checked={formData.scope_type === 'general'}
                    onChange={() => setFormData({ ...formData, scope_type: 'general', price_list_id: '' })}
                  />
                  <div>
                    <div className="title">General</div>
                    <div className="desc">Aplica sobre el costo base del producto para todos los clientes</div>
                  </div>
                </label>

                <label className={`discounts-manager__scope-card ${formData.scope_type === 'price_list' ? 'discounts-manager__scope-card--active' : ''}`}>
                  <input
                    type="radio"
                    name="scope_type"
                    value="price_list"
                    checked={formData.scope_type === 'price_list'}
                    onChange={() => setFormData({ ...formData, scope_type: 'price_list' })}
                  />
                  <div>
                    <div className="title">Por Lista de Precios</div>
                    <div className="desc">Aplica sobre (base + markup) para clientes de una lista específica (Prioridad 1)</div>
                  </div>
                </label>
              </div>
            </div>

            {/* Selector de Lista si aplica */}
            {formData.scope_type === 'price_list' && (
              <div>
                <label className="label discounts-manager__field-label">Lista de Precios Destino *</label>
                <select
                  className="input"
                  value={formData.price_list_id}
                  onChange={(e) => setFormData({ ...formData, price_list_id: e.target.value })}
                  required
                >
                  <option value="">-- Selecciona una lista de precios --</option>
                  {priceLists.map(pl => (
                    <option key={pl.price_list_id} value={pl.price_list_id}>
                      {pl.list_name} (ID: {pl.price_list_id})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Porcentaje */}
            <div>
              <label className="label discounts-manager__field-label">Porcentaje de Descuento (%) *</label>
              <div className="discounts-manager__input-with-icon">
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="100"
                  className="input"
                  placeholder="Ej: 15.00"
                  value={formData.discount_percentage}
                  onChange={(e) => setFormData({ ...formData, discount_percentage: e.target.value })}
                  required
                />
                <FontAwesomeIcon icon={faPercentage} className="icon-suffix" />
              </div>

              {/* Vista Previa de Precios en Vivo */}
              {selectedProduct && formData.discount_percentage && !isNaN(parseFloat(formData.discount_percentage)) && parseFloat(formData.discount_percentage) > 0 && (() => {
                const pct = parseFloat(formData.discount_percentage) || 0;
                const basePrice = parseFloat(selectedProduct.base_price || selectedProduct.original_price || 0);
                const ivaPct = parseFloat(selectedProduct.iva_percentage || 16.0);
                
                // Cálculo según ámbito
                const isPriceList = formData.scope_type === 'price_list';
                const markupPct = isPriceList ? parseFloat(selectedProduct.markup_percentage || 0) : 0;
                const origPrice = isPriceList && markupPct > 0 
                  ? basePrice * (1 + markupPct / 100)
                  : basePrice;
                const discAmount = origPrice * (pct / 100);
                const finalNet = origPrice - discAmount;
                const finalWithIva = selectedProduct.final_price != null 
                  ? parseFloat(selectedProduct.final_price) * (1 - pct / 100) 
                  : finalNet * (1 + ivaPct / 100);

                return (
                  <div className="discounts-manager__calc-preview">
                    <div className="discounts-manager__calc-item">
                      <div className="label">
                        {isPriceList ? 'Precio Lista (Base+Markup)' : 'Precio Base Original'}
                      </div>
                      <div className="val">
                        ${origPrice.toFixed(2)}
                      </div>
                    </div>

                    <div className="discounts-manager__calc-item">
                      <div className="label">Descuento ({pct}%)</div>
                      <div className="val val--danger">
                        -${discAmount.toFixed(2)}
                      </div>
                    </div>

                    <div className="discounts-manager__calc-item">
                      <div className="label">Precio con Descuento</div>
                      <div className="val val--success">
                        ${finalNet.toFixed(2)}
                      </div>
                    </div>

                    <div className="discounts-manager__calc-item">
                      <div className="label">Estimado Final (+IVA)</div>
                      <div className="val val--primary">
                        ${finalWithIva.toFixed(2)}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Fechas */}
            <div className="discounts-manager__grid-2">
              <div>
                <label className="label discounts-manager__field-label">Fecha Inicio *</label>
                <input
                  type="datetime-local"
                  className="input"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="label discounts-manager__field-label">Fecha Expiración *</label>
                <input
                  type="datetime-local"
                  className="input"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  required
                />
              </div>
            </div>

            {/* Descripción / Campaña */}
            <div>
              <label className="label discounts-manager__field-label">Descripción / Motivo (Opcional)</label>
              <input
                type="text"
                className="input"
                placeholder="Ej: Oferta de temporada, Campaña Verano, etc."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>

            {/* Checkbox Activo */}
            <div className="discounts-manager__checkbox-row">
              <input
                type="checkbox"
                id="discount_is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              />
              <label htmlFor="discount_is_active">
                Descuento activo inmediatamente
              </label>
            </div>
          </div>

          <div className="modal__footer discounts-manager__modal-footer">
            <button type="button" className="btn btn--secondary" onClick={onClose} disabled={formSubmitting}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--primary" disabled={formSubmitting}>
              {formSubmitting ? 'Guardando...' : (editingDiscount ? 'Actualizar Descuento' : 'Crear Descuento')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
