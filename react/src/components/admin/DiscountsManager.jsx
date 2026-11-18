import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlus } from '@fortawesome/free-solid-svg-icons';

import discountService from '../../services/discountService';
import { productService } from '../../services/productService';
import priceListService from '../../services/priceListService';
import { toDateTimeLocalString, mexicoLocalToUtcIso, formatMexicoDateTime } from '../../utils/formatUtils';
import ErrorMessage from '../common/ErrorMessage';
import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

import DiscountsSummaryCards from './discounts/DiscountsSummaryCards';
import DiscountsFilterBar from './discounts/DiscountsFilterBar';
import DiscountsTable from './discounts/DiscountsTable';
import DiscountFormModal from './discounts/DiscountFormModal';

export default function DiscountsManager() {
  const { can } = usePermissions();
  const canManageDiscounts = can(PERMISSIONS.CATALOG_DISCOUNTS);
  const [discounts, setDiscounts] = useState([]);
  const [priceLists, setPriceLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [filterScope, setFilterScope] = useState('all'); // all, general, price_list
  const [filterActive, setFilterActive] = useState('all'); // all, active, inactive, vigente

  // Paginación
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const { limit: itemsPerPage } = usePaginationLimit();

  // Modal Crear / Editar
  const [showModal, setShowModal] = useState(false);
  const [editingDiscount, setEditingDiscount] = useState(null);
  const [formData, setFormData] = useState({
    product_id: '',
    scope_type: 'general', // 'general' o 'price_list'
    price_list_id: '',
    discount_percentage: '',
    start_date: '',
    end_date: '',
    description: '',
    is_active: true
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  // Búsqueda de productos en modal
  const [productSearch, setProductSearch] = useState('');
  const [productSearchResults, setProductSearchResults] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [searchingProducts, setSearchingProducts] = useState(false);

  // Estadísticas server-side
  const [stats, setStats] = useState({ total: 0, active: 0, general: 0, price_list: 0 });

  useEffect(() => {
    loadPriceLists();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
      setPage(0);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    loadDiscounts();
  }, [page, itemsPerPage, filterActive, debouncedSearchTerm]);

  useEffect(() => {
    setPage(0);
  }, [itemsPerPage]);

  const loadPriceLists = async () => {
    try {
      const data = await priceListService.getPriceLists({ limit: 100 });
      setPriceLists(data || []);
    } catch (err) {
      console.error('Error cargando listas de precios:', err);
    }
  };

  const loadStats = async () => {
    try {
      const res = await discountService.getDiscountStats();
      if (res) {
        setStats(res);
      }
    } catch (err) {
      console.error('Error cargando estadísticas de descuentos:', err);
    }
  };

  const loadDiscounts = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        skip: page * itemsPerPage,
        limit: itemsPerPage + 1
      };
      if (filterActive === 'vigente') {
        params.only_current = true;
      } else if (filterActive === 'active') {
        params.is_active = true;
      } else if (filterActive === 'inactive') {
        params.is_active = false;
      }
      if (debouncedSearchTerm.trim()) params.search = debouncedSearchTerm.trim();

      const data = await discountService.getDiscounts(params);
      const items = Array.isArray(data) ? data : (data?.items || []);

      if (items.length > itemsPerPage) {
        setHasMore(true);
        setDiscounts(items.slice(0, itemsPerPage));
      } else {
        setHasMore(false);
        setDiscounts(items);
      }
      loadStats();
    } catch (err) {
      console.error('Error cargando descuentos:', err);
      setError('Error al obtener el listado de promociones y descuentos.');
      setDiscounts([]);
    } finally {
      setLoading(false);
    }
  };

  // Autocompletado de productos
  useEffect(() => {
    if (!productSearch || productSearch.length < 2) {
      setProductSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        setSearchingProducts(true);
        const data = await productService.getProducts({ search: productSearch, limit: 8 });
        const list = Array.isArray(data) ? data : (data?.items || []);
        setProductSearchResults(list);
      } catch (err) {
        console.error('Error buscando productos:', err);
      } finally {
        setSearchingProducts(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [productSearch]);

  const openCreateModal = () => {
    setEditingDiscount(null);
    setSelectedProduct(null);
    setProductSearch('');
    setProductSearchResults([]);
    setFormError(null);

    const now = new Date();
    const nextMonth = new Date(now);
    nextMonth.setMonth(nextMonth.getMonth() + 1);

    setFormData({
      product_id: '',
      scope_type: 'general',
      price_list_id: '',
      discount_percentage: '',
      start_date: toDateTimeLocalString(now),
      end_date: toDateTimeLocalString(nextMonth),
      description: '',
      is_active: true
    });
    setShowModal(true);
  };

  const openEditModal = (discount) => {
    setEditingDiscount(discount);
    setSelectedProduct({
      product_id: discount.product_id,
      name: discount.product_name || discount.product?.name || discount.product_id,
      base_price: discount.original_price
    });
    setFormError(null);

    setFormData({
      product_id: discount.product_id,
      scope_type: discount.price_list_id ? 'price_list' : 'general',
      price_list_id: discount.price_list_id || '',
      discount_percentage: discount.discount_percentage,
      start_date: toDateTimeLocalString(discount.start_date),
      end_date: toDateTimeLocalString(discount.end_date),
      description: discount.description || '',
      is_active: discount.is_active
    });
    setShowModal(true);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!selectedProduct && !editingDiscount) {
      setFormError('Debes seleccionar un producto.');
      return;
    }

    const pct = parseFloat(formData.discount_percentage);
    if (isNaN(pct) || pct <= 0 || pct > 100) {
      setFormError('El porcentaje debe estar entre 0.01 y 100%.');
      return;
    }

    if (!formData.start_date || !formData.end_date) {
      setFormError('Las fechas de inicio y expiración son obligatorias.');
      return;
    }

    if (new Date(formData.end_date) <= new Date(formData.start_date)) {
      setFormError('La fecha de fin debe ser posterior a la fecha de inicio.');
      return;
    }

    if (formData.scope_type === 'price_list' && !formData.price_list_id) {
      setFormError('Debes seleccionar la lista de precios destino.');
      return;
    }

    try {
      setFormSubmitting(true);
      const payload = {
        product_id: editingDiscount ? editingDiscount.product_id : selectedProduct.product_id,
        price_list_id: formData.scope_type === 'price_list' ? parseInt(formData.price_list_id, 10) : null,
        discount_percentage: pct,
        start_date: mexicoLocalToUtcIso(formData.start_date),
        end_date: mexicoLocalToUtcIso(formData.end_date),
        description: formData.description?.trim() || null,
        is_active: formData.is_active
      };

      if (editingDiscount) {
        await discountService.updateDiscount(editingDiscount.discount_id, payload);
        setSuccessMsg('Descuento actualizado correctamente.');
      } else {
        await discountService.createDiscount(payload);
        setSuccessMsg('Descuento creado exitosamente.');
      }

      setShowModal(false);
      loadDiscounts();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      console.error('Error guardando descuento:', err);
      const detail = err.response?.data?.detail || err.message || 'Error al guardar descuento.';
      setFormError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleToggleActive = async (discount) => {
    try {
      await discountService.updateDiscount(discount.discount_id, {
        is_active: !discount.is_active
      });
      loadDiscounts();
    } catch (err) {
      console.error('Error cambiando estado:', err);
      setError('No se pudo actualizar el estado del descuento.');
    }
  };

  const handleDelete = async (discount) => {
    const scopeLabel = discount.price_list_id ? `la lista #${discount.price_list_id}` : 'General';
    if (!window.confirm(`¿Eliminar descuento del ${discount.discount_percentage}% para ${discount.product_id} (${scopeLabel})?`)) return;

    try {
      await discountService.deleteDiscount(discount.discount_id);
      setSuccessMsg('Descuento eliminado correctamente.');
      loadDiscounts();
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      console.error('Error eliminando descuento:', err);
      setError('Error al eliminar el descuento.');
    }
  };

  // Filtrado en memoria por ámbito y búsqueda local si aplica
  const filteredDiscounts = discounts.filter((d) => {
    if (filterScope === 'general' && d.price_list_id !== null) return false;
    if (filterScope === 'price_list' && d.price_list_id === null) return false;

    if (searchTerm.trim()) {
      const terms = searchTerm.trim().toLowerCase().split(/\s+/);
      const plistName = priceLists.find(p => p.price_list_id === d.price_list_id)?.list_name || '';
      return terms.every(term => (
        d.product_id?.toLowerCase().includes(term) ||
        d.product_name?.toLowerCase().includes(term) ||
        d.description?.toLowerCase().includes(term) ||
        d.price_list_name?.toLowerCase().includes(term) ||
        plistName.toLowerCase().includes(term)
      ));
    }
    return true;
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return formatMexicoDateTime(dateStr, {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const isVigente = (startStr, endStr, isActive) => {
    if (!isActive) return false;
    const now = new Date();
    return new Date(startStr) <= now && new Date(endStr) >= now;
  };

  return (
    <section className="dashboard-section">
      <div className="discounts-manager__header">
        <div>
          <h2 className="section-title">Descuentos y Promociones</h2>
          <p className="text-muted">
            Aplica descuentos directos sobre el precio base o específicos por lista de precios.
          </p>
        </div>
        {canManageDiscounts && (
          <button className="btn btn--primary" onClick={openCreateModal}>
            <FontAwesomeIcon icon={faPlus} className="mr-2" />
            Nuevo Descuento
          </button>
        )}
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}
      {successMsg && (
        <div className="discounts-manager__alert-success">
          {successMsg}
        </div>
      )}

      {/* Tarjetas de Métricas Server-Side */}
      <DiscountsSummaryCards stats={stats} />

      {/* Barra de Búsqueda y Filtros */}
      <DiscountsFilterBar
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        filterScope={filterScope}
        setFilterScope={setFilterScope}
        filterActive={filterActive}
        setFilterActive={setFilterActive}
        setPage={setPage}
      />

      {/* Tabla de Descuentos con Paginación */}
      <DiscountsTable
        loading={loading}
        filteredDiscounts={filteredDiscounts}
        priceLists={priceLists}
        canManageDiscounts={canManageDiscounts}
        formatDate={formatDate}
        isVigente={isVigente}
        handleToggleActive={handleToggleActive}
        openEditModal={openEditModal}
        handleDelete={handleDelete}
        page={page}
        setPage={setPage}
        hasMore={hasMore}
        totalDiscountsCount={discounts.length}
      />

      {/* Modal Crear / Editar Descuento */}
      <DiscountFormModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        editingDiscount={editingDiscount}
        formData={formData}
        setFormData={setFormData}
        formSubmitting={formSubmitting}
        formError={formError}
        handleFormSubmit={handleFormSubmit}
        selectedProduct={selectedProduct}
        setSelectedProduct={setSelectedProduct}
        productSearch={productSearch}
        setProductSearch={setProductSearch}
        searchingProducts={searchingProducts}
        productSearchResults={productSearchResults}
        setProductSearchResults={setProductSearchResults}
        priceLists={priceLists}
      />
    </section>
  );
}
