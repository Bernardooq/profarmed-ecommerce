import { useState, useEffect, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faBookmark,
  faTrashAlt,
  faCircleNotch,
  faReceipt,
  faUser,
  faCalendarAlt,
  faBoxesStacked,
  faChevronLeft,
  faChevronRight,
  faInfoCircle,
} from '@fortawesome/free-solid-svg-icons';
import { productService } from '../../../services/productService';
import { formatCurrency } from '../../../utils/formatUtils';
import usePermissions from '../../../hooks/usePermissions';
import { PERMISSIONS } from '../../../config/permissions';

const PAGE_SIZE = 10;

const STATUS_LABELS = {
  pending_validation: 'Pendiente Validación',
  assigned: 'Asignado',
  approved: 'Aprobado',
  shipped: 'Enviado',
  delivered: 'Entregado',
  cancelled: 'Cancelado',
};

const STATUS_COLORS = {
  pending_validation: 'badge--warning',
  assigned: 'badge--info',
  approved: 'badge--success',
  shipped: 'badge--primary',
  delivered: 'badge--secondary',
  cancelled: 'badge--danger',
};

export default function ModalProductStockHolds({ isOpen, onClose, product, onHoldDeleted, canDelete = true }) {
  const { can, isAdmin } = usePermissions();
  const canDeleteHolds = canDelete && (
    isAdmin ||
    (can(PERMISSIONS.CATALOG_VIEW) && (can(PERMISSIONS.PRODUCTS_STOCK) || can(PERMISSIONS.PRODUCTS_EDIT)))
  );

  const [loading, setLoading] = useState(false);
  const [deletingOrderId, setDeletingOrderId] = useState(null);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [holdsData, setHoldsData] = useState({
    product_id: '',
    product_name: '',
    total_holds: 0,
    total_quantity: 0,
    items: [],
  });
  const [page, setPage] = useState(0);

  const loadHolds = useCallback(async (targetPage = 0) => {
    if (!product?.product_id) return;
    setLoading(true);
    setError('');
    try {
      const data = await productService.getProductStockHolds(product.product_id, {
        skip: targetPage * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      setHoldsData(data || { total_holds: 0, total_quantity: 0, items: [] });
      setPage(targetPage);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al cargar los apartados del producto');
    } finally {
      setLoading(false);
    }
  }, [product?.product_id]);

  useEffect(() => {
    if (isOpen && product?.product_id) {
      setSuccessMsg('');
      loadHolds(0);
    }
  }, [isOpen, product?.product_id, loadHolds]);

  const handleDeleteHold = async (orderId, quantity) => {
    if (!window.confirm(`¿Liberar el apartado de ${quantity} pieza(s) de la orden #${orderId}?`)) {
      return;
    }

    setDeletingOrderId(orderId);
    setError('');
    setSuccessMsg('');

    try {
      const res = await productService.deleteProductStockHold(product.product_id, orderId);
      setSuccessMsg(res?.message || `Apartado de la orden #${orderId} liberado con éxito`);
      await loadHolds(page);
      if (onHoldDeleted) {
        onHoldDeleted(product.product_id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al liberar el apartado');
    } finally {
      setDeletingOrderId(null);
    }
  };

  if (!isOpen || !product) return null;

  const totalPages = Math.ceil((holdsData.total_holds || 0) / PAGE_SIZE);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal modal--lg"
        style={{ maxWidth: '820px', width: '95%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__header">
          <div className="d-flex align-items-center gap-2">
            <FontAwesomeIcon icon={faBookmark} className="text-warning" />
            <h3 className="m-0 text-lg">Apartados en Reserva (order_stock_holds)</h3>
          </div>
          <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">&times;</button>
        </div>

        <div className="modal__body p-3 p-md-4" style={{ overflowY: 'auto' }}>
          {/* Card resumen del producto */}
          <div className="card p-3 mb-3 bg-light rounded border">
            <div className="d-flex justify-content-between align-items-start mb-2 flex-wrap gap-2">
              <div>
                <span className="text-xs text-muted d-block">Producto:</span>
                <strong className="text-base font-bold">{product.name}</strong>
              </div>
              <span className="badge badge--secondary font-mono">ID: {product.product_id}</span>
            </div>

            <div className="d-flex gap-3 pt-2 border-top text-xs flex-wrap">
              <div className="d-flex align-items-center gap-1">
                <span className="text-muted">Stock Físico ERP:</span>{' '}
                <strong className="text-dark font-mono">{product.stock_count ?? 0}</strong>
              </div>
              <div className="d-flex align-items-center gap-1">
                <span className="text-muted">Total en Reserva:</span>{' '}
                <span className="badge badge--warning font-mono font-bold">
                  {holdsData.total_quantity} pzas
                </span>
              </div>
              <div className="d-flex align-items-center gap-1">
                <span className="text-muted">Pedidos con Reserva:</span>{' '}
                <strong className="font-mono">{holdsData.total_holds}</strong>
              </div>
            </div>
          </div>

          {error && <div className="alert alert--danger mb-3">{error}</div>}
          {successMsg && <div className="alert alert--success mb-3">{successMsg}</div>}

          {/* Listado de apartados */}
          {loading && holdsData.items.length === 0 ? (
            <div className="text-center py-5">
              <FontAwesomeIcon icon={faCircleNotch} spin size="2x" className="text-primary mb-2" />
              <p className="text-muted text-sm">Consultando apartados activos...</p>
            </div>
          ) : holdsData.items.length === 0 ? (
            <div className="empty-state text-center py-5 border rounded bg-white">
              <div className="text-muted mb-2" style={{ fontSize: '2rem' }}>
                <FontAwesomeIcon icon={faBoxesStacked} />
              </div>
              <h4 className="text-sm font-bold text-dark mb-1">Sin apartados activos</h4>
              <p className="text-xs text-muted mb-0">
                Este producto no cuenta con unidades apartadas por órdenes en proceso.
              </p>
            </div>
          ) : (
            <div className="table-responsive border rounded bg-white">
              <table className="data-table m-0">
                <thead>
                  <tr>
                    <th>Orden</th>
                    <th>Cliente</th>
                    <th className="text-center">Estado</th>
                    <th className="text-end">Total Orden</th>
                    <th className="text-center">Piezas Apartadas</th>
                    <th>Fecha Apartado</th>
                    {canDeleteHolds && <th className="text-end">Acción</th>}
                  </tr>
                </thead>
                <tbody>
                  {holdsData.items.map((hold) => (
                    <tr key={hold.order_id}>
                      <td data-label="Orden" className="font-bold">
                        <span className="d-flex align-items-center gap-1 font-mono">
                          <FontAwesomeIcon icon={faReceipt} className="text-muted" />
                          #{hold.order_id}
                        </span>
                      </td>
                      <td data-label="Cliente">
                        <div className="d-flex align-items-center gap-1">
                          <FontAwesomeIcon icon={faUser} className="text-muted" />
                          <span title={hold.customer_name}>{hold.customer_name}</span>
                        </div>
                      </td>
                      <td data-label="Estado" className="text-center">
                        <span className={`badge ${STATUS_COLORS[hold.order_status] || 'badge--secondary'}`}>
                          {STATUS_LABELS[hold.order_status] || hold.order_status}
                        </span>
                      </td>
                      <td data-label="Total Orden" className="text-end font-mono">
                        {hold.order_total != null ? formatCurrency(hold.order_total) : '—'}
                      </td>
                      <td data-label="Piezas Apartadas" className="text-center font-mono font-bold text-warning" style={{ fontSize: '0.95rem' }}>
                        {hold.quantity}
                      </td>
                      <td data-label="Fecha Apartado" className="text-muted">
                        <div className="d-flex align-items-center gap-1">
                          <FontAwesomeIcon icon={faCalendarAlt} className="text-muted" />
                          <span>
                            {hold.created_at
                              ? new Date(hold.created_at).toLocaleDateString('es-MX', {
                                  year: 'numeric',
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })
                              : '—'}
                          </span>
                        </div>
                      </td>
                      {canDeleteHolds && (
                        <td data-label="Acción" className="text-end">
                          <button
                            type="button"
                            className="btn btn--danger btn--xs d-inline-flex align-items-center gap-1"
                            onClick={() => handleDeleteHold(hold.order_id, hold.quantity)}
                            disabled={deletingOrderId === hold.order_id}
                            title={`Liberar apartado de ${hold.quantity} piezas`}
                          >
                            {deletingOrderId === hold.order_id ? (
                              <FontAwesomeIcon icon={faCircleNotch} spin />
                            ) : (
                              <FontAwesomeIcon icon={faTrashAlt} />
                            )}
                            <span>Liberar</span>
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Paginación */}
          {totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center pt-3 border-top mt-3">
              <span className="text-xs text-muted">
                Página {page + 1} de {totalPages} ({holdsData.total_holds} registros)
              </span>
              <div className="d-flex gap-1">
                <button
                  type="button"
                  className="btn btn--secondary btn--xs"
                  onClick={() => loadHolds(page - 1)}
                  disabled={page <= 0 || loading}
                >
                  <FontAwesomeIcon icon={faChevronLeft} /> Anterior
                </button>
                <button
                  type="button"
                  className="btn btn--secondary btn--xs"
                  onClick={() => loadHolds(page + 1)}
                  disabled={page >= totalPages - 1 || loading}
                >
                  Siguiente <FontAwesomeIcon icon={faChevronRight} />
                </button>
              </div>
            </div>
          )}

          <div className="mt-3 p-2 bg-light rounded text-xs text-muted d-flex align-items-center gap-2 border">
            <FontAwesomeIcon icon={faInfoCircle} className="text-info" />
            <span>
              Al liberar un apartado, las piezas reservadas por la orden vuelven a estar disponibles en el catálogo para el resto de clientes.
            </span>
          </div>
        </div>

        <div className="modal__footer p-3 border-top d-flex justify-content-end">
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
