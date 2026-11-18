import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPencilAlt, faTrashAlt, faBoxes, faEye, faBookmark } from '@fortawesome/free-solid-svg-icons';
import { formatCurrency } from '../../utils/formatUtils';
import { getProductImageUrl } from '../../utils/imageUtils';

const LOW_STOCK_THRESHOLD = 10;
const DEFAULT_IVA = 16;

export default function ProductRow({
  product,
  onEdit,
  onDelete,
  onUpdateStock,
  onUpdateReservedStock,
  onView,
  onPreviewImage,
  isAdmin = true,
  canViewCost = isAdmin,
  canUpdateStock = isAdmin,
  canEdit = isAdmin,
  canDelete = isAdmin,
  showReservedStock = false,
  canEditReservedStock = false
}) {
  const getStockClass = (stock) => {
    if (stock === 0) return 'out';
    if (stock < LOW_STOCK_THRESHOLD) return 'low';
    return 'ok';
  };

  const stockCount = product.stock_count ?? 0;
  const stockClass = getStockClass(stockCount);
  const stockLabel = stockClass === 'out' ? 'Agotado' :
    stockClass === 'low' ? `Bajo (${stockCount})` :
      stockCount;

  const basePrice = parseFloat(product.base_price) || 0;
  const ivaPercentage = parseFloat(product.iva_percentage) ?? DEFAULT_IVA;

  return (
    <tr>
      <td data-label="Img">
        <img
          className="product-thumb"
          src={getProductImageUrl(product)}
          alt={product.name}
          loading="lazy"
          onError={(e) => { e.target.src = '/images/default-product.svg'; }}
          onClick={() => onPreviewImage && onPreviewImage(getProductImageUrl(product), product.name)}
        />
      </td>
      <td data-label="ID">{product.product_id}</td>
      <td data-label="Producto">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
          {product.lock && <span title="Producto Bloqueado (Lock)" style={{ cursor: 'help' }}>🔒</span>}
          {product.display_priority !== undefined && product.display_priority !== null && product.display_priority < 1000000 && (
            <span className="badge badge--primary" title={`Prioridad Fijada en Catálogo: #${product.display_priority}`} style={{ fontSize: '0.72rem', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
              ⭐ #{product.display_priority}
            </span>
          )}
          <span>{product.name}</span>
        </div>
      </td>
      <td data-label="codebar">{product.codebar}</td>
      <td data-label="Categoría">{product.category?.name || 'N/A'}</td>
      <td data-label="Ubicación">
        {product.location ? (
          <span className="badge badge--location">📍 {product.location}</span>
        ) : (
          <span className="text-muted">—</span>
        )}
      </td>
      {canViewCost && <td data-label="Precio Base">{formatCurrency(basePrice)}</td>}
      <td data-label="IVA">
        {ivaPercentage.toFixed(0)}%
      </td>
      <td data-label="Stock Actual">
        <span className={`stock-badge stock-badge--${stockClass}`}>
          {stockLabel}
        </span>
      </td>
      {showReservedStock && (
        <td data-label="En Reserva" className="text-center">
          <span
            className={`badge ${product.reserved_stock > 0 ? 'badge--warning' : 'badge--secondary'} font-mono font-bold`}
            style={{ cursor: canEditReservedStock ? 'pointer' : 'default' }}
            onClick={(e) => {
              if (canEditReservedStock) {
                e.stopPropagation();
                onUpdateReservedStock(product);
              }
            }}
            title={canEditReservedStock ? "Ver apartados en reserva (order.apartar)" : "Stock en reserva"}
          >
            {product.reserved_stock ?? 0}
          </span>
        </td>
      )}
      <td data-label="Acciones" className="actions-cell">
        <div className="d-flex gap-1">
          <button
            className="btn btn--icon btn--ghost"
            onClick={(e) => { e.stopPropagation(); onView(product); }}
            title="Ver Detalles"
          >
            <FontAwesomeIcon icon={faEye} />
          </button>

          {canEditReservedStock && showReservedStock && (
            <button
              className="btn btn--icon btn--ghost text-warning"
              aria-label="Ver Apartados de Reserva"
              onClick={(e) => { e.stopPropagation(); onUpdateReservedStock(product); }}
              title="Ver y Gestionar Apartados (order.apartar)"
            >
              <FontAwesomeIcon icon={faBookmark} />
            </button>
          )}

          {canUpdateStock && (
            <button
              className="btn btn--icon btn--ghost"
              aria-label="Actualizar Stock"
              onClick={(e) => { e.stopPropagation(); onUpdateStock(product); }}
              title="Actualizar Stock"
            >
              <FontAwesomeIcon icon={faBoxes} />
            </button>
          )}
          {canEdit && (
            <button
              className="btn btn--icon btn--ghost"
              aria-label="Editar Producto"
              onClick={(e) => { e.stopPropagation(); onEdit(product); }}
              title="Editar Producto"
            >
              <FontAwesomeIcon icon={faPencilAlt} />
            </button>
          )}
          {canDelete && (
            <button
              className="btn btn--icon btn--danger"
              aria-label="Eliminar Producto"
              onClick={(e) => { e.stopPropagation(); onDelete(product); }}
              title="Eliminar Producto"
            >
              <FontAwesomeIcon icon={faTrashAlt} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
