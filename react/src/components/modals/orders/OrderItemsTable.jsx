import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTrash } from '@fortawesome/free-solid-svg-icons';
import { formatCurrency } from '../../../utils/formatUtils';

export default function OrderItemsTable({ items, onQuantityChange, onQuantityBlur, onRemoveItem, loading }) {
    const calculateTotal = () => items.reduce((sum, item) => sum + (item.final_price * item.quantity), 0);

    return (
        <>
            <h3 className="mb-3">Productos del Pedido</h3>
            <div className="table-container">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Producto</th>
                            <th>Descripción</th>
                            <th>Precio Unit.</th>
                            <th>Cantidad</th>
                            <th>Subtotal</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.length === 0 ? (
                            <tr><td colSpan="6" className="text-center">No hay productos en el pedido</td></tr>
                        ) : (
                            items.map((item, index) => (
                                <tr key={index}>
                                    <td data-label="Producto">
                                        <strong>{item.product_name}</strong>
                                        {item.product?.location && (
                                            <div className="mt-1">
                                                <span className="badge badge--location">
                                                    📍 {item.product.location}
                                                </span>
                                            </div>
                                        )}
                                        {item.has_discount && item.discount_applied > 0 && (
                                            <span className="badge badge--discount badge--sm">
                                                -{item.discount_applied}% {item.discount_type === 'price_list' ? 'Lista' : 'Promo'}
                                            </span>
                                        )}
                                    </td>
                                    <td data-label="Descripción">
                                        <span className="text-muted text-sm">
                                            {item.product?.description || item.description || item.product?.descripcion_2 || '—'}
                                        </span>
                                    </td>
                                    <td data-label="Precio Unit.">
                                        {item.has_discount && item.original_price ? (
                                            <div>
                                                <span className="price-strike price-strike--sm">
                                                    {formatCurrency(item.original_price)}
                                                </span>
                                                <strong className="text-danger">{formatCurrency(item.final_price)}</strong>
                                            </div>
                                        ) : (
                                            formatCurrency(item.final_price)
                                        )}
                                    </td>
                                    <td data-label="Cantidad">
                                        <input className="input input--sm table-qty-input" type="number" value={item.quantity} onChange={(e) => onQuantityChange(index, e.target.value)} onBlur={() => onQuantityBlur?.(index)} min="1" disabled={loading} />
                                    </td>
                                    <td data-label="Subtotal">{formatCurrency(item.final_price * item.quantity)}</td>
                                    <td data-label="Acciones">
                                        <button className="btn btn--icon btn--danger" onClick={() => onRemoveItem(index)} title="Eliminar producto" disabled={loading}>
                                            <FontAwesomeIcon icon={faTrash} />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            <div className="text-right text-lg font-bold mt-4">
                Total: {formatCurrency(calculateTotal())}
            </div>
        </>
    );
}

