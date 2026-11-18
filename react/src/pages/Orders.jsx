import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SearchBar from '../components/layout/SearchBar';
import Footer from '../components/layout/Footer';
import OrderHistory from '../components/orders/OrderHistory';
import PaginationButtons from '../components/common/PaginationButtons';
import HelpGuide from '../components/common/HelpGuide';
import OrderModal from '../components/orders/OrderModal';
import TicketCreateModal from '../components/modals/tickets/TicketCreateModal';
import orderService from '../services/orderService';
import { formatCurrency } from '../utils/formatUtils';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faShoppingBag, faSpinner } from '@fortawesome/free-solid-svg-icons';
import usePermissions from '../hooks/usePermissions';

const ORDERS_PER_PAGE = 10;

const STATUS_LABELS = {
  'pending_validation': 'Validando',
  'approved': 'Aprobado',
  'shipped': 'Enviado',
  'delivered': 'Entregado',
  'cancelled': 'Cancelado'
};

const STATUS_CLASSES = {
  'pending_validation': 'pending',
  'approved': 'confirmed',
  'shipped': 'shipped',
  'delivered': 'delivered',
  'cancelled': 'cancelled'
};

export default function Orders() {
  const { user } = useAuth();
  const { isCustomer, getDashboardPath } = usePermissions();
  const navigate = useNavigate();

  const [orders, setOrders] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [ticketOrder, setTicketOrder] = useState(null);
  const [showTicketModal, setShowTicketModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);

  useEffect(() => {
    // Si es personal operativo (staff), redirigir directamente a la consola operativa de gestión
    if (user && !isCustomer) {
      navigate(getDashboardPath ? getDashboardPath() : '/dashboard');
    }
  }, [user, isCustomer, navigate, getDashboardPath]);

  useEffect(() => {
    loadOrders();
  }, [page]);

  const loadOrders = async () => {
    try {
      setLoading(true);
      const data = await orderService.getOrders({ skip: page * ORDERS_PER_PAGE, limit: ORDERS_PER_PAGE });

      let itemsList = [];
      let pages = 0;
      if (data && Array.isArray(data.items)) {
        itemsList = data.items;
        pages = data.lookahead_pages;
      } else {
        const isArray = Array.isArray(data);
        itemsList = isArray ? data : (data?.items || []);
        pages = 0;
      }
      setLookaheadPages(pages);

      const completedOrders = itemsList.map(order => ({
        id: `FC-${order.order_id}`,
        orderId: order.order_id,
        date: new Date(order.created_at).toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' }),
        total: `${formatCurrency(order.total_amount)} MXN`,
        totalAmount: parseFloat(order.total_amount),
        subtotal: (order.items || []).reduce((sum, item) => sum + (parseFloat(item.final_price) * item.quantity), 0),
        shippingCost: parseFloat(order.shipping_cost || 0),
        status: STATUS_LABELS[order.status] || order.status,
        statusClass: STATUS_CLASSES[order.status] || 'pending',
        rawStatus: order.status,
        shippingAddress: order.shipping_address || 'No especificada',
        invoice_type: order.invoice_type || 'factura',
        order_notes: order.order_notes || null,
        items: (order.items || []).map(item => ({
          name: item.product?.name || 'Producto',
          quantity: item.quantity,
          price: parseFloat(item.final_price),
          subtotal: parseFloat(item.final_price) * item.quantity,
          product: item.product
        }))
      }));
      setOrders(completedOrders);
    } catch (err) {
      console.error('Error loading orders:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelOrder = async (order) => {
    if (!window.confirm(`¿Estás seguro de cancelar el pedido ${order.id}?`)) return;
    try {
      setLoading(true);
      await orderService.cancelOrder(order.orderId);
      alert('Pedido cancelado exitosamente');
      await loadOrders();
    } catch (err) {
      console.error('Error canceling order:', err);
      alert('Error al cancelar el pedido');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenTicketForOrder = (order) => {
    setTicketOrder(order);
    setShowTicketModal(true);
  };

  return (
    <div className="page">
      <SearchBar />

      <main className="page__content">
        <div className="page-container">
          <div className="d-flex items-center justify-between mb-6 flex-wrap gap-4">
            <div>
              <h1 className="section-title">
                <FontAwesomeIcon icon={faShoppingBag} className="mr-2 text-primary" />
                Mis Pedidos
              </h1>
              <p className="text-sm text-muted">Historial completo y seguimiento de tus pedidos.</p>
            </div>
            <HelpGuide
              title="Guía de Pedidos"
              items={[
                "Estado 'Validando': El pedido fue registrado y está pendiente de validación por tu agente.",
                "Cancelación: Puedes cancelar pedidos únicamente mientras se encuentren en estado 'Validando'.",
                "Detalles: Haz clic en cualquier pedido para ver el desglose de productos y su dirección de entrega.",
                "Reportar Incidencia: Usa el botón '🎫 Reportar' para abrir un ticket de soporte directamente vinculado a ese pedido."
              ]}
            />
          </div>

          {loading && orders.length === 0 ? (
            <div className="empty-state">
              <FontAwesomeIcon icon={faSpinner} spin className="empty-state__icon text-primary" />
              <div className="empty-state__text">Cargando tus pedidos...</div>
            </div>
          ) : (
            <>
              <OrderHistory
                orders={orders}
                onSelectOrder={setSelectedOrder}
                onCancelOrder={handleCancelOrder}
                onOpenTicket={handleOpenTicketForOrder}
              />

              {orders.length > 0 && (
                <PaginationButtons
                  currentPage={page}
                  lookaheadPages={lookaheadPages}
                  onPageChange={setPage}
                />
              )}
            </>
          )}
        </div>
      </main>

      <Footer />

      {selectedOrder && (
        <OrderModal
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
          onReportTicket={handleOpenTicketForOrder}
        />
      )}

      <TicketCreateModal
        isOpen={showTicketModal}
        onClose={() => {
          setShowTicketModal(false);
          setTicketOrder(null);
        }}
        onTicketCreated={() => {
          alert('¡Ticket de soporte creado con éxito! Puedes consultar su seguimiento en la sección de Soporte.');
          setShowTicketModal(false);
          setTicketOrder(null);
        }}
        initialOrderId={ticketOrder?.orderId}
        lockOrderId={true}
      />
    </div>
  );
}
