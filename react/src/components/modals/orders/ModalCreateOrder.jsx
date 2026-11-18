import { useState, useEffect } from 'react';
import orderService from '../../../services/orderService';
import ErrorMessage from '../../common/ErrorMessage';
import { formatCurrency } from '../../../utils/formatUtils';
import CustomerSelector from './CustomerSelector';
import OrderItemsTable from './OrderItemsTable';
import ProductSearchGrid from './ProductSearchGrid';
import SimilarProductsModal from './SimilarProductsModal';
import StockConflictBanner from './StockConflictBanner';

export default function ModalCreateOrder({ visible, onClose, onSuccess }) {
    const [selectedCustomer, setSelectedCustomer] = useState(null);
    const [shippingAddressNumber, setShippingAddressNumber] = useState(1);
    const [items, setItems] = useState([]);
    const [shippingCost, setShippingCost] = useState(0);
    const [orderNotes, setOrderNotes] = useState('');
    const [assignmentNotes, setAssignmentNotes] = useState('');
    const [invoiceType, setInvoiceType] = useState('factura');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showSimilarModal, setShowSimilarModal] = useState(false);
    const [selectedProductForSimilar, setSelectedProductForSimilar] = useState(null);
    const [stockConflict, setStockConflict] = useState(null); // { productName, stock, existingQty, quantity, totalQty, maxCanAdd, doAdd }

    useEffect(() => { if (!visible) { setSelectedCustomer(null); setItems([]); setShippingCost(0); setOrderNotes(''); setAssignmentNotes(''); setInvoiceType('factura'); setError(null); setShowSimilarModal(false); setSelectedProductForSimilar(null); setStockConflict(null); setShippingAddressNumber(1); } }, [visible]);

    const handleQuantityChange = (index, newQuantity) => {
        const newQty = Math.max(1, parseInt(newQuantity) || 1);
        const item = items[index];
        const stock = item.stock_count || 0;

        // Siempre actualizar para que el input no quede bloqueado
        const updated = [...items];
        updated[index].quantity = newQty;
        setItems(updated);

        if (stock > 0 && newQty > stock) {
            // Mostrar banner no-bloqueante — se actualiza si el user sigue editando
            const doSet = (qty) => {
                setItems(prev => { const u = [...prev]; u[index].quantity = qty; return u; });
                setStockConflict(null);
            };
            setStockConflict({
                productName: item.product_name,
                stock,
                existingQty: item.quantity,
                quantity: newQty,
                totalQty: newQty,
                maxCanAdd: stock,
                doAdd: doSet,
            });
        } else {
            setStockConflict(null); // Limpiar si vuelve a un valor válido
        }
    };

    const handleRemoveItem = (index) => setItems(items.filter((_, i) => i !== index));

    const handleQuantityBlur = () => {
        if (stockConflict) {
            document.querySelector('.stock-conflict-banner')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    };

    const handleAddProductToOrder = (product, quantity = 1) => {
        const stock = product.stock_count || 0;
        const existingIndex = items.findIndex(item => item.product_id === product.product_id);
        const existingQty = existingIndex >= 0 ? items[existingIndex].quantity : 0;
        const totalQty = existingQty + quantity;

        const doAdd = (qtyToAdd) => {
            if (existingIndex >= 0) {
                const updated = [...items];
                updated[existingIndex].quantity += qtyToAdd;
                setItems(updated);
            } else {
                setItems(prev => [...prev, {
                product_id: product.product_id,
                product_name: product.name,
                quantity: qtyToAdd,
                final_price: product.final_price,
                stock_count: stock,
                has_discount: product.has_discount,
                discount_applied: product.discount_applied,
                discount_type: product.discount_type,
                original_price: product.original_price,
                base_price: product.base_price
            }]);
            }
            setStockConflict(null);
        };

        const maxCanAdd = stock - existingQty;

        if (stock === 0 || totalQty > stock) {
            // Mostrar banner de conflicto con 3 opciones
            setStockConflict({
                productName: product.name,
                stock,
                existingQty,
                quantity,
                totalQty,
                maxCanAdd: Math.max(0, maxCanAdd),
                doAdd,
            });
            return;
        }

        // Stock suficiente — agregar normalmente
        doAdd(quantity);
    };

    const handleShowSimilar = (product) => { setSelectedProductForSimilar(product); setShowSimilarModal(true); };

    const handleCreateOrder = async () => {
        if (!selectedCustomer) { setError('Debe seleccionar un cliente'); return; }
        if (items.length === 0) { setError('El pedido debe tener al menos un producto'); return; }
        setLoading(true); setError(null);
        try {
            const newOrder = await orderService.createOrderForCustomer({
                customer_id: selectedCustomer.customer_id,
                items: items.map(item => ({ product_id: item.product_id, quantity: item.quantity })),
                shipping_address_number: shippingAddressNumber,
                shipping_cost: shippingCost,
                order_notes: orderNotes || null,
                assignment_notes: assignmentNotes || null,
                invoice_type: invoiceType || 'factura'
            });
            window.alert(`✅ ¡Pedido #${newOrder.order_id || 'creado'} exitosamente!\n\nEl pedido se ha guardado en el sistema.\n(Nota: Si el cliente tiene otro vendedor por defecto, es posible que este pedido no aparezca en tu tabla personal).`);
            onSuccess?.(); onClose();
        } catch (err) { setError(err.response?.data?.detail || err.message || 'Error al crear pedido'); }
        finally { setLoading(false); }
    };

    if (!visible) return null;

    return (
        <>
            <div className="modal-overlay" onClick={onClose}>
                <div className="modal modal--lg" onClick={(e) => e.stopPropagation()}>
                    <div className="modal__header">
                        <h2>Crear Pedido para Cliente</h2>
                        <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">&times;</button>
                    </div>
                    <div className="modal__body">
                        {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

                        {!selectedCustomer ? (
                            <CustomerSelector onSelect={setSelectedCustomer} visible={visible} />
                        ) : (
                            <>
                                <div className="card mb-4 p-3">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="mb-1"><strong>Cliente:</strong> {selectedCustomer.full_name}</p>
                                            <p className="mb-0"><strong>Email:</strong> {selectedCustomer.email}</p>
                                        </div>
                                        <button type="button" className="btn btn--secondary btn--sm" onClick={() => { setSelectedCustomer(null); setItems([]); setShippingAddressNumber(1); }} disabled={loading}>
                                            Cambiar Cliente
                                        </button>
                                    </div>

                                    <div className="form-group mt-3 mb-0">
                                        <label className="form-group__label" htmlFor="shipping-address-select">
                                            Dirección de Entrega:
                                        </label>
                                        <select
                                            id="shipping-address-select"
                                            className="select"
                                            value={shippingAddressNumber}
                                            onChange={(e) => setShippingAddressNumber(parseInt(e.target.value))}
                                            disabled={loading}
                                        >
                                            <option value={1}>
                                                Dirección 1 (Principal): {selectedCustomer.address_1 || 'No registrada'}
                                            </option>
                                            {selectedCustomer.address_2 && selectedCustomer.address_2.trim() && (
                                                <option value={2}>
                                                    Dirección 2: {selectedCustomer.address_2}
                                                </option>
                                            )}
                                            {selectedCustomer.address_3 && selectedCustomer.address_3.trim() && (
                                                <option value={3}>
                                                    Dirección 3: {selectedCustomer.address_3}
                                                </option>
                                            )}
                                        </select>
                                    </div>
                                </div>

                                <OrderItemsTable items={items} onQuantityChange={handleQuantityChange} onQuantityBlur={handleQuantityBlur} onRemoveItem={handleRemoveItem} loading={loading} />

                                {stockConflict && (
                                    <StockConflictBanner
                                        conflict={stockConflict}
                                        onOverride={() => stockConflict.doAdd(stockConflict.quantity)}
                                        onAdjust={() => stockConflict.doAdd(stockConflict.maxCanAdd)}
                                        onCancel={() => setStockConflict(null)}
                                    />
                                )}

                                <ProductSearchGrid customerId={selectedCustomer.customer_id} onAddToOrder={handleAddProductToOrder} onShowSimilar={handleShowSimilar} />

                                {/* Tipo de Comprobante (Factura / Remisión) */}
                                <div className="form-group mt-6">
                                    <label className="form-group__label" htmlFor="create-invoice-type">
                                        Tipo de Comprobante
                                    </label>
                                    <select
                                        id="create-invoice-type"
                                        className="input"
                                        value={invoiceType}
                                        onChange={(e) => setInvoiceType(e.target.value)}
                                        disabled={loading}
                                    >
                                        <option value="factura">Factura</option>
                                        <option value="remision">Remisión</option>
                                    </select>
                                </div>

                                {/* Notas del Pedido (cliente) */}
                                <div className="form-group mt-3">
                                    <label className="form-group__label" htmlFor="create-order-notes">
                                        Notas del Cliente <span className="text-muted">(Opcional — el cliente las verá)</span>
                                    </label>
                                    <textarea
                                        id="create-order-notes"
                                        className="input"
                                        rows={2}
                                        value={orderNotes}
                                        onChange={(e) => setOrderNotes(e.target.value)}
                                        placeholder="Ej: Productos de lotes recientes, revisar fechas de caducidad..."
                                        disabled={loading}
                                    />
                                </div>

                                {/* Notas al Vendedor (internas) */}
                                <div className="form-group mt-3">
                                    <label className="form-group__label" htmlFor="create-assignment-notes">
                                        Notas al Vendedor 📋 <span className="text-muted">(Solo staff interno)</span>
                                    </label>
                                    <textarea
                                        id="create-assignment-notes"
                                        className="input"
                                        rows={2}
                                        value={assignmentNotes}
                                        onChange={(e) => setAssignmentNotes(e.target.value)}
                                        placeholder="Ej: Cliente VIP, entregar hoy, requiere factura..."
                                        disabled={loading}
                                    />
                                </div>

                                {/* Resumen del Pedido */}
                                <div className="order-summary mt-4">
                                    <div className="order-summary__row">
                                        <span>Subtotal Productos:</span>
                                        <span>{formatCurrency(items.reduce((sum, item) => sum + (item.quantity * item.final_price), 0))}</span>
                                    </div>
                                    <div className="order-summary__row">
                                        <span>Costo de Envío:</span>
                                        <input
                                            id="shipping-cost-create"
                                            type="number"
                                            min="0"
                                            step="0.01"
                                            value={shippingCost}
                                            onChange={(e) => {
                                                const value = parseFloat(e.target.value);
                                                setShippingCost(isNaN(value) || value < 0 ? 0 : value);
                                            }}
                                            placeholder="0.00"
                                            className="input input--sm"
                                        />
                                    </div>
                                    <div className="order-summary__row order-summary__total">
                                        <strong>Total:</strong>
                                        <span className="order-summary__total-amount">
                                            {formatCurrency(items.reduce((sum, item) => sum + (item.quantity * item.final_price), 0) + Number(shippingCost))}
                                        </span>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                    <div className="modal__footer">
                        <button type="button" className="btn btn--secondary" onClick={onClose} disabled={loading}>Cancelar</button>
                        {selectedCustomer && (
                            <button type="button" className="btn btn--primary" onClick={handleCreateOrder} disabled={loading || items.length === 0}>
                                {loading ? 'Creando...' : 'Crear Pedido'}
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <SimilarProductsModal visible={showSimilarModal} product={selectedProductForSimilar} customerId={selectedCustomer?.customer_id} onAddToOrder={handleAddProductToOrder} onClose={() => setShowSimilarModal(false)} />
        </>
    );
}
