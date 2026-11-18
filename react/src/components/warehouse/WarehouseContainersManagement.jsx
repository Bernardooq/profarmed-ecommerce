import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faRotate, faPlus, faCheckCircle, faExclamationTriangle
} from '@fortawesome/free-solid-svg-icons';
import warehouseService from '../../services/warehouseService';
import ErrorMessage from '../common/ErrorMessage';
import PaginationButtons from '../common/PaginationButtons';
import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

// Subcomponentes desacoplados del dominio de Canastas QR
import ContainersStatsGrid from './containers/ContainersStatsGrid';
import ContainersFilterControls from './containers/ContainersFilterControls';
import ContainersTable from './containers/ContainersTable';
import ModalCreateContainer from './containers/ModalCreateContainer';
import ModalDeleteContainer from './containers/ModalDeleteContainer';
import ModalContainerQR from './ModalContainerQR';

/**
 * WarehouseContainersManagement
 * Vista principal de administración del parque físico de canastas QR (Totes de bodega).
 * Desacoplado en componentes modulares reutilizables.
 */
export default function WarehouseContainersManagement() {
  const { can, isAdmin } = usePermissions();
  const canManageContainers = isAdmin || can(PERMISSIONS.WAREHOUSE_CONTAINERS) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canRelease = isAdmin || can(PERMISSIONS.WAREHOUSE_CONTAINERS) || can(PERMISSIONS.WAREHOUSE_MANAGE) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR) || can(PERMISSIONS.WAREHOUSE_OPERATOR);

  const { limit: itemsPerPage } = usePaginationLimit();
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [stats, setStats] = useState({ total: 0, available: 0, in_use: 0, maintenance: 0, retired: 0 });

  const [containers, setContainers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState(null);

  // Filtros
  const [statusFilter, setStatusFilter] = useState(''); // '' | 'available' | 'in_use' | 'maintenance' | 'retired'
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Modales
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedContainerForQr, setSelectedContainerForQr] = useState(null);
  const [deletingContainer, setDeletingContainer] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  // Feedback copiado
  const [copiedId, setCopiedId] = useState(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(0);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Reset page when filter or itemsPerPage changes
  useEffect(() => {
    setPage(0);
  }, [statusFilter, itemsPerPage]);

  const loadStats = async () => {
    try {
      const res = await warehouseService.getContainersStats();
      if (res && typeof res === 'object') {
        setStats(res);
      }
    } catch (err) {
      console.error('Error al cargar stats de canastas:', err);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadContainers();
  }, [page, statusFilter, debouncedSearch, itemsPerPage]);

  const loadContainers = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        skip: page * itemsPerPage,
        limit: itemsPerPage + 1
      };
      if (statusFilter) params.status = statusFilter;
      if (debouncedSearch.trim()) params.search = debouncedSearch.trim();

      const data = await warehouseService.getContainers(params);
      if (Array.isArray(data)) {
        setHasMore(data.length > itemsPerPage);
        setContainers(data.slice(0, itemsPerPage));
      } else {
        setContainers([]);
        setHasMore(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al cargar catálogo de canastas QR');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyText = (text, id) => {
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreate = async (cleanQr) => {
    const created = await warehouseService.createContainer(cleanQr);
    setFeedback({ type: 'success', text: `Canasta '${cleanQr}' registrada exitosamente.` });
    setShowCreateModal(false);
    await Promise.all([loadContainers(), loadStats()]);
    if (created) {
      setSelectedContainerForQr(created);
    }
  };

  const handleUpdateStatus = async (container, newStatus) => {
    if (!canManageContainers) return;
    try {
      setLoading(true);
      await warehouseService.updateContainerStatus(container.container_id, newStatus);
      const statusLabels = {
        available: '🟢 Disponible',
        maintenance: '🟡 En Mantenimiento',
        retired: '🔴 Retirada (Baja)',
        unavailable: '⚪ No Disponible'
      };
      setFeedback({
        type: 'success',
        text: `Canasta ${container.qr_code} actualizada a: ${statusLabels[newStatus] || newStatus}`
      });
      if (deletingContainer && deletingContainer.container_id === container.container_id) {
        setDeletingContainer(null);
      }
      await Promise.all([loadContainers(), loadStats()]);
    } catch (err) {
      setFeedback({ type: 'error', text: err.response?.data?.detail || err.message || 'Error al actualizar estatus' });
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  const handleRelease = async (container, emptyItems = false) => {
    if (!canRelease) return;
    try {
      setLoading(true);
      await warehouseService.releaseContainer({ container_id: container.container_id, empty_items: emptyItems });
      setFeedback({
        type: 'success',
        text: `Canasta ${container.qr_code} liberada exitosamente y devuelta al parque disponible.`
      });
      await Promise.all([loadContainers(), loadStats()]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || '';
      if (!emptyItems && detail.includes('Confirma el vaciado')) {
        if (window.confirm(`${detail}\n\n¿Deseas FORZAR el vaciado de las piezas depositadas para devolverlas a 'pendientes' y liberar la canasta?`)) {
          return handleRelease(container, true);
        }
      }
      setFeedback({ type: 'error', text: detail || 'Error al liberar canasta' });
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  const confirmDelete = async () => {
    if (!deletingContainer) return;
    try {
      setDeleting(true);
      setDeleteError(null);
      await warehouseService.deleteContainer(deletingContainer.container_id);
      setFeedback({
        type: 'success',
        text: `Canasta ${deletingContainer.qr_code} eliminada del sistema.`
      });
      setDeletingContainer(null);
      await Promise.all([loadContainers(), loadStats()]);
      setTimeout(() => setFeedback(null), 5000);
    } catch (err) {
      setDeleteError(err.response?.data?.detail || err.message || 'Error al eliminar canasta');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="warehouse-containers">
      {/* Encabezado estandarizado */}
      <div className="warehouse-manager__header">
        <div>
          <h2>
            <span>🧺</span> Parque Físico de Canastas QR (Totes de Bodega)
          </h2>
          <p>
            Administración, trazabilidad y estado operativo de canastas QR reutilizables para surtido y revisión.
          </p>
        </div>
        <div className="d-flex align-items-center gap-2">
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={loadContainers}
            disabled={loading}
            title="Recargar catálogo de canastas"
          >
            <FontAwesomeIcon icon={faRotate} spin={loading} className="me-1" />
            Actualizar
          </button>
          {canManageContainers && (
            <button
              type="button"
              className="btn btn--primary btn--sm font-bold"
              onClick={() => setShowCreateModal(true)}
            >
              <FontAwesomeIcon icon={faPlus} className="me-1" />
              Nueva Canasta QR
            </button>
          )}
        </div>
      </div>

      {/* Alertas de Feedback */}
      {feedback && (
        <div className={`alert ${feedback.type === 'success' ? 'alert--success' : 'alert--danger'} mb-4`}>
          <FontAwesomeIcon icon={feedback.type === 'success' ? faCheckCircle : faExclamationTriangle} className="me-2" />
          {feedback.text}
        </div>
      )}

      {error && <ErrorMessage message={error} />}

      {/* Grid de Métricas / KPIs */}
      <ContainersStatsGrid
        stats={stats}
        statusFilter={statusFilter}
        onSelectFilter={setStatusFilter}
      />

      {/* Barra de Filtros y Búsqueda */}
      <ContainersFilterControls
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        onSearchSubmit={(val) => {
          setDebouncedSearch(val);
          setPage(0);
        }}
        statusFilter={statusFilter}
        onSelectFilter={setStatusFilter}
        stats={stats}
      />

      {/* Tabla Desacoplada de Canastas */}
      <ContainersTable
        containers={containers}
        loading={loading}
        canManageContainers={canManageContainers}
        canRelease={canRelease}
        copiedId={copiedId}
        onCopyText={handleCopyText}
        onSelectContainerForQr={setSelectedContainerForQr}
        onReleaseContainer={handleRelease}
        onUpdateStatus={handleUpdateStatus}
        onDeleteContainer={(c) => {
          setDeleteError(null);
          setDeletingContainer(c);
        }}
        onOpenCreateModal={() => setShowCreateModal(true)}
      />

      {/* Paginación Estandarizada Backend-Side */}
      <PaginationButtons
        onPrev={() => setPage((prev) => Math.max(0, prev - 1))}
        onNext={() => setPage((prev) => prev + 1)}
        canGoPrev={page > 0}
        canGoNext={hasMore}
        page={page}
      />

      {/* Modal: Visor y Copiador de Imagen QR / Impresión */}
      {selectedContainerForQr && (
        <ModalContainerQR
          container={selectedContainerForQr}
          isOpen={Boolean(selectedContainerForQr)}
          onClose={() => setSelectedContainerForQr(null)}
        />
      )}

      {/* Modal: Alta de Nueva Canasta QR */}
      <ModalCreateContainer
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreate}
      />

      {/* Modal: Confirmar Eliminación con regla de trazabilidad */}
      <ModalDeleteContainer
        container={deletingContainer}
        isOpen={Boolean(deletingContainer)}
        onClose={() => {
          setDeletingContainer(null);
          setDeleteError(null);
        }}
        onConfirmDelete={confirmDelete}
        onRetireContainer={(c) => {
          setDeletingContainer(null);
          setDeleteError(null);
          handleUpdateStatus(c, 'retired');
        }}
        deleting={deleting}
        error={deleteError}
      />
    </div>
  );
}
