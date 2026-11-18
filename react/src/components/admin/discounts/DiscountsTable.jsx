import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faPencilAlt, faTrashAlt, faToggleOn, faToggleOff 
} from '@fortawesome/free-solid-svg-icons';
import LoadingSpinner from '../../common/LoadingSpinner';
import PaginationButtons from '../../common/PaginationButtons';

export default function DiscountsTable({
  loading,
  filteredDiscounts,
  priceLists,
  canManageDiscounts,
  formatDate,
  isVigente,
  handleToggleActive,
  openEditModal,
  handleDelete,
  page,
  setPage,
  hasMore,
  totalDiscountsCount
}) {
  if (loading) {
    return <LoadingSpinner message="Cargando promociones y descuentos..." />;
  }

  return (
    <>
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Producto</th>
              <th>Ámbito / Aplicación</th>
              <th>Descuento</th>
              <th>Vigencia</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {filteredDiscounts.length === 0 ? (
              <tr>
                <td colSpan="6" className="discounts-manager__empty-text">
                  No se encontraron descuentos configurados con los filtros actuales.
                </td>
              </tr>
            ) : (
              filteredDiscounts.map((discount) => {
                const activeNow = isVigente(discount.start_date, discount.end_date, discount.is_active);
                const isGeneral = discount.price_list_id === null;
                const plist = priceLists.find(p => p.price_list_id === discount.price_list_id);

                return (
                  <tr key={discount.discount_id}>
                    <td data-label="Producto">
                      <div className="discounts-manager__product-id">{discount.product_id}</div>
                      <div className="discounts-manager__product-name">
                        {discount.product_name || discount.product?.name || 'Producto sin nombre'}
                      </div>
                    </td>
                    <td data-label="Ámbito">
                      {isGeneral ? (
                        <span className="status-badge discounts-manager__badge-general">
                          🌐 General (Base)
                        </span>
                      ) : (
                        <span className="status-badge discounts-manager__badge-list">
                          🏷️ Lista: {plist?.list_name || `#${discount.price_list_id}`}
                        </span>
                      )}
                      {discount.description && (
                        <div className="discounts-manager__desc-muted">
                          {discount.description}
                        </div>
                      )}
                    </td>
                    <td data-label="Descuento y Precios">
                      <span className="discounts-manager__price-pill">
                        -{discount.discount_percentage}%
                      </span>
                      {discount.original_price != null ? (
                        <div className="discounts-manager__price-details">
                          <div className="discounts-manager__price-orig">
                            Orig: <span>${parseFloat(discount.original_price).toFixed(2)}</span>
                          </div>
                          <div className="discounts-manager__price-desc">
                            Desc: ${parseFloat(discount.discounted_price).toFixed(2)}
                            <span>(-${parseFloat(discount.discount_amount).toFixed(2)})</span>
                          </div>
                          {discount.final_price_with_iva != null && (
                            <div className="discounts-manager__price-final">
                              Final c/IVA: <strong>${parseFloat(discount.final_price_with_iva).toFixed(2)}</strong>
                            </div>
                          )}
                        </div>
                      ) : null}
                    </td>
                    <td data-label="Vigencia">
                      <div className="discounts-manager__validity">
                        <div><strong>Inicio:</strong> {formatDate(discount.start_date)}</div>
                        <div><strong>Fin:</strong> {formatDate(discount.end_date)}</div>
                        <div className="discounts-manager__creator">
                          <span>👤 Creado por:</span>
                          <strong>{discount.created_by_name || 'Admin'}</strong>
                        </div>
                      </div>
                    </td>
                    <td data-label="Estado">
                      <div className="discounts-manager__status-row">
                        <span className={`status-badge ${activeNow ? 'status--active' : 'status--inactive'}`}>
                          {activeNow ? 'Vigente' : (discount.is_active ? 'Fuera de Fecha' : 'Inactivo')}
                        </span>
                        {canManageDiscounts && (
                          <button
                            type="button"
                            className={`btn btn--icon btn--ghost discounts-manager__toggle-btn ${discount.is_active ? 'discounts-manager__toggle-btn--active' : ''}`}
                            onClick={() => handleToggleActive(discount)}
                            title={discount.is_active ? 'Desactivar' : 'Activar'}
                          >
                            <FontAwesomeIcon icon={discount.is_active ? faToggleOn : faToggleOff} size="lg" />
                          </button>
                        )}
                      </div>
                    </td>
                    <td data-label="Acciones" className="actions-cell">
                      {canManageDiscounts ? (
                        <>
                          <button
                            className="btn btn--icon btn--ghost"
                            onClick={() => openEditModal(discount)}
                            title="Editar Descuento"
                          >
                            <FontAwesomeIcon icon={faPencilAlt} />
                          </button>
                          <button
                            className="btn btn--icon btn--danger"
                            onClick={() => handleDelete(discount)}
                            title="Eliminar Descuento"
                          >
                            <FontAwesomeIcon icon={faTrashAlt} />
                          </button>
                        </>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {totalDiscountsCount > 0 && (
        <PaginationButtons
          onPrev={() => setPage(p => Math.max(0, p - 1))}
          onNext={() => setPage(p => p + 1)}
          canGoPrev={page > 0}
          canGoNext={hasMore}
        />
      )}
    </>
  );
}
