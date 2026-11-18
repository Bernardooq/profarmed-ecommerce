import { useState, useEffect } from 'react';
import priceListService from '../../services/priceListService';
import ModalPriceListForm from '../modals/priceLists/ModalPriceListForm';
import ModalPriceListItems from '../modals/priceLists/ModalPriceListItems';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import PaginationButtons from '../common/PaginationButtons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPencilAlt, faTrashAlt, faList, faDownload } from '@fortawesome/free-solid-svg-icons';

import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function PriceListManager() {
  const { can, isAdmin } = usePermissions();
  const canManagePrices = isAdmin || can(PERMISSIONS.CATALOG_PRICES);
  const canViewPublicPrices = isAdmin || can(PERMISSIONS.CATALOG_PRICES) || can(PERMISSIONS.CATALOG_PRICES_PUBLIC);
  const canExportPrices = canManagePrices || can(PERMISSIONS.REPORTS_EXPORT);
  const [priceLists, setPriceLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const { limit: itemsPerPage } = usePaginationLimit();

  const [showFormModal, setShowFormModal] = useState(false);
  const [showItemsModal, setShowItemsModal] = useState(false);
  const [selectedPriceList, setSelectedPriceList] = useState(null);

  useEffect(() => { loadPriceLists(); }, [page, itemsPerPage]);

  const loadPriceLists = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        skip: page * itemsPerPage,
        limit: itemsPerPage + 1
      };
      const data = await priceListService.getPriceLists(params);
      const results = data || [];
      const hasMorePages = results.length > itemsPerPage;
      setHasMore(hasMorePages);
      setPriceLists(hasMorePages ? results.slice(0, itemsPerPage) : results);
    } catch (err) {
      setError('No se pudieron cargar las listas de precios');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => { setSelectedPriceList(null); setShowFormModal(true); };
  const handleEdit = (priceList) => { setSelectedPriceList(priceList); setShowFormModal(true); };
  const handleManageItems = (priceList) => { setSelectedPriceList(priceList); setShowItemsModal(true); };

  const handleExport = async (priceList) => {
    try {
      await priceListService.exportPriceList(priceList.price_list_id);
    } catch (err) {
      setError(err.message || 'Error al exportar la lista de precios');
      console.error(err);
    }
  };

  const handleDelete = async (priceList) => {
    if (!window.confirm(`¿Estás seguro de eliminar la lista "${priceList.list_name}"?`)) return;
    try {
      await priceListService.deletePriceList(priceList.price_list_id);
      if (page === 0) {
        await loadPriceLists();
      } else {
        setPage(0);
      }
    } catch (err) {
      setError('Error al eliminar la lista de precios');
      console.error(err);
    }
  };

  const handleFormSuccess = async () => {
    setShowFormModal(false);
    setSelectedPriceList(null);
    if (page === 0) {
      await loadPriceLists();
    } else {
      setPage(0);
    }
  };

  return (
    <section className="dashboard-section">
      <div className="section-header">
        <h2 className="section-title">Listas de Precios</h2>
        {canManagePrices && (
          <button className="btn btn--primary btn--sm" onClick={handleCreate}>
            + Nueva Lista
          </button>
        )}
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      {loading ? (
        <LoadingSpinner message="Cargando listas de precios..." />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Estado</th>
                <th>Visibilidad</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {priceLists.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-8">No hay listas de precios creadas</td>
                </tr>
              ) : (
                priceLists.map((priceList) => (
                  <tr key={priceList.price_list_id}>
                    <td data-label="ID">{priceList.price_list_id}</td>
                    <td data-label="Nombre">{priceList.list_name}</td>
                    <td data-label="Descripción">{priceList.description || 'N/A'}</td>
                    <td data-label="Estado">
                      <span className={`status-badge ${priceList.is_active ? 'status--active' : 'status--inactive'}`}>
                        {priceList.is_active ? 'Activa' : 'Inactiva'}
                      </span>
                    </td>
                    <td data-label="Visibilidad">
                      <div className="d-flex flex-wrap gap-1">
                        {priceList.is_public_internal && (
                          <span className="badge badge--info" title="Pública para agentes de venta y personal autorizado">
                            Interna
                          </span>
                        )}
                        {priceList.is_public_storefront && (
                          <span className="badge badge--success" title="Pública en tienda web general">
                            Web
                          </span>
                        )}
                        {!priceList.is_public_internal && !priceList.is_public_storefront && (
                          <span className="badge badge--secondary" title="Lista privada asignada por cliente">
                            Privada
                          </span>
                        )}
                      </div>
                    </td>
                    <td data-label="Acciones" className="actions-cell">
                      {canViewPublicPrices && (
                        <button className="btn btn--icon btn--ghost" onClick={() => handleManageItems(priceList)} aria-label="Ver Productos" title="Ver Productos">
                          <FontAwesomeIcon icon={faList} />
                        </button>
                      )}
                      {canExportPrices && (
                        <button className="btn btn--icon btn--ghost" onClick={() => handleExport(priceList)} aria-label="Exportar Lista" title="Exportar">
                          <FontAwesomeIcon icon={faDownload} />
                        </button>
                      )}
                      {canManagePrices && (
                        <>
                          <button className="btn btn--icon btn--ghost" onClick={() => handleEdit(priceList)} aria-label="Editar Lista" title="Editar">
                            <FontAwesomeIcon icon={faPencilAlt} />
                          </button>
                          <button className="btn btn--icon btn--danger" onClick={() => handleDelete(priceList)} aria-label="Eliminar Lista" title="Eliminar">
                            <FontAwesomeIcon icon={faTrashAlt} />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {priceLists.length > 0 && (
        <PaginationButtons
          onPrev={() => setPage(p => Math.max(0, p - 1))}
          onNext={() => setPage(p => p + 1)}
          canGoPrev={page > 0}
          canGoNext={hasMore}
        />
      )}

      {showFormModal && (
        <ModalPriceListForm
          isOpen={showFormModal}
          onClose={() => { setShowFormModal(false); setSelectedPriceList(null); }}
          onSuccess={handleFormSuccess}
          priceList={selectedPriceList}
        />
      )}

      {showItemsModal && (
        <ModalPriceListItems
          isOpen={showItemsModal}
          onClose={() => { setShowItemsModal(false); setSelectedPriceList(null); }}
          priceList={selectedPriceList}
        />
      )}
    </section>
  );
}
