import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faSliders, faSearch, faTimes, faCheck,
  faBan, faCircleNotch, faRotate, faInfoCircle,
  faToggleOn, faToggleOff, faClock
} from '@fortawesome/free-solid-svg-icons';
import adminService from '../../services/adminService';
import productService from '../../services/productService';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import PaginationButtons from '../common/PaginationButtons';
import ItemsPerPageSelector from '../common/ItemsPerPageSelector';
import { usePaginationLimit } from '../../context/PaginationLimitContext';

export default function SystemConfigsModal({ isOpen, onClose }) {
  const { limit: itemsPerPage } = usePaginationLimit();
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [updatingId, setUpdatingId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [shuffling, setShuffling] = useState(false);

  useEffect(() => {
    setPage(0);
  }, [itemsPerPage]);

  useEffect(() => {
    if (isOpen) {
      loadConfigs(appliedSearch, page);
    }
  }, [isOpen, page, appliedSearch, itemsPerPage]);

  const loadConfigs = async (query = appliedSearch, targetPage = page) => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        skip: targetPage * itemsPerPage,
        limit: itemsPerPage + 1
      };
      if (query && query.trim()) params.search = query.trim();
      const res = await adminService.getSystemConfigs(params);
      if (Array.isArray(res)) {
        setHasMore(res.length > itemsPerPage);
        setConfigs(res.slice(0, itemsPerPage));
      } else {
        setConfigs([]);
        setHasMore(false);
      }
    } catch (err) {
      console.error('Error al cargar system_configs:', err);
      setError(err.response?.data?.detail || err.message || 'Error al obtener configuraciones');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(0);
    setAppliedSearch(searchTerm);
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    setPage(0);
    setAppliedSearch('');
  };

  const handleToggle = async (config) => {
    const newStatus = !config.is_active;
    try {
      setUpdatingId(config.config_id);
      setError(null);
      await adminService.updateSystemConfigStatus(config.config_id, newStatus);
      setConfigs(prev =>
        prev.map(c => c.config_id === config.config_id ? { ...c, is_active: newStatus } : c)
      );
      setFeedbackMsg(`Configuración "${config.config_name}" ${newStatus ? 'activada' : 'desactivada'} correctamente.`);
      setTimeout(() => setFeedbackMsg(null), 3500);
    } catch (err) {
      console.error('Error al actualizar system_config:', err);
      setError(err.response?.data?.detail || err.message || 'No se pudo actualizar el estado de la configuración.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleShuffleNow = async () => {
    if (!window.confirm('¿Deseas barajar el catálogo rotativo ahora? Solo reordenará productos sin prioridad manual fijada (display_priority >= 1,000,000).')) {
      return;
    }
    try {
      setShuffling(true);
      setError(null);
      const res = await productService.shuffleCatalog();
      setFeedbackMsg(res.message || 'Catálogo rotativo barajado correctamente.');
      setTimeout(() => setFeedbackMsg(null), 4000);
    } catch (err) {
      console.error('Error al barajar catálogo:', err);
      setError(err.response?.data?.detail || err.message || 'No se pudo barajar el catálogo.');
    } finally {
      setShuffling(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal modal--lg"
        style={{ maxWidth: '850px', width: '95%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__header">
          <div className="d-flex align-items-center gap-2">
            <FontAwesomeIcon icon={faSliders} className="text-primary text-xl" />
            <div>
              <h3 className="modal__title m-0">Configuraciones Globales del Sistema</h3>
              <span className="text-xs text-muted">
                Banderas operacionales y directivas activas (system_configs)
              </span>
            </div>
          </div>
          <button
            type="button"
            className="modal__close"
            onClick={onClose}
            aria-label="Cerrar modal"
          >
            &times;
          </button>
        </div>

        <div className="modal__body p-3 p-md-4" style={{ overflowY: 'auto' }}>
          {error && <ErrorMessage message={error} />}
          {feedbackMsg && (
            <div className="alert alert--success mb-3 d-flex align-items-center gap-2">
              <FontAwesomeIcon icon={faCheck} />
              <span>{feedbackMsg}</span>
            </div>
          )}

          {/* Barra de búsqueda server-side, selector por página y refresco */}
          <form onSubmit={handleSearchSubmit} className="d-flex align-items-center gap-2 mb-3 flex-wrap">
            <div className="search-bar flex-1 position-relative" style={{ minWidth: 0, flexBasis: '180px' }}>
              <input
                type="text"
                className="input input--search w-full"
                placeholder="Buscar por clave o descripción..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              {searchTerm && (
                <button
                  type="button"
                  className="btn btn--icon btn--ghost position-absolute right-2 top-50 translate-middle-y"
                  onClick={handleClearSearch}
                  title="Limpiar búsqueda"
                >
                  <FontAwesomeIcon icon={faTimes} className="text-muted" />
                </button>
              )}
            </div>
            <div className="d-flex align-items-center gap-2 flex-wrap" style={{ flexShrink: 0 }}>
              <button type="submit" className="btn btn--primary d-flex align-items-center gap-2">
                <FontAwesomeIcon icon={faSearch} />
                <span className="hidden-phone">Buscar</span>
              </button>
              <button
                type="button"
                className="btn btn--secondary btn--icon"
                onClick={() => loadConfigs(appliedSearch, page)}
                title="Recargar lista"
                disabled={loading}
              >
                <FontAwesomeIcon icon={faRotate} spin={loading} />
              </button>
              <ItemsPerPageSelector />
            </div>
          </form>

          {/* Listado / Tabla de configs */}
          {loading ? (
            <div className="text-center py-5">
              <LoadingSpinner />
              <p className="text-muted text-sm mt-2">Cargando directivas de configuración...</p>
            </div>
          ) : configs.length === 0 ? (
            <div className="text-center py-5">
              <FontAwesomeIcon icon={faBan} className="text-muted text-3xl mb-2" />
              <p className="text-muted font-bold m-0">No se encontraron configuraciones.</p>
              <small className="text-muted">Prueba con otro término de búsqueda.</small>
            </div>
          ) : (
            <div className="table-responsive border rounded bg-white" style={{ maxHeight: '55vh', overflowY: 'auto' }}>
              <table className="data-table m-0 w-full">
                <thead>
                  <tr>
                    <th style={{ width: '80px' }} className="text-center">ID</th>
                    <th>Configuración / Clave</th>
                    <th>Descripción Operacional</th>
                    <th style={{ width: '130px' }} className="text-center">Estado</th>
                    <th style={{ width: '140px', minWidth: '140px' }} className="text-center">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {configs.map((conf) => {
                    const isUpdating = updatingId === conf.config_id;
                    return (
                      <tr key={conf.config_id} className={conf.is_active ? 'bg-light-success' : ''}>
                        <td data-label="ID" className="text-center font-mono font-bold text-muted">
                          #{conf.config_id}
                        </td>
                        <td data-label="Configuración">
                          <div className="font-mono font-bold text-primary">
                            {conf.config_name}
                          </div>
                        </td>
                        <td data-label="Descripción" className="text-sm">
                          <div className="text-muted">
                            {conf.description || '— Sin descripción asignada —'}
                          </div>
                          {conf.config_name === 'catalog.weekly_rotation' && (
                            <div className="mt-2 d-flex align-items-center gap-2 flex-wrap">
                              <span className="badge badge--info font-xs d-inline-flex align-items-center gap-1 font-bold">
                                <FontAwesomeIcon icon={faClock} /> Auto: Domingos 3:00 AM (cronjob)
                              </span>
                              <button
                                type="button"
                                className="btn btn--xs btn--primary d-inline-flex align-items-center gap-1 font-bold shadow-sm"
                                onClick={handleShuffleNow}
                                disabled={shuffling}
                                title="Barajar manualmente ahora los productos rotativos (>= 1,000,000)"
                              >
                                <FontAwesomeIcon icon={shuffling ? faCircleNotch : faRotate} spin={shuffling} />
                                <span>{shuffling ? 'Barajando catálogo...' : '🎲 Barajar Ahora'}</span>
                              </button>
                            </div>
                          )}
                        </td>
                        <td data-label="Estado" className="text-center">
                          {conf.is_active ? (
                            <span className="badge badge--success font-bold d-inline-flex align-items-center gap-1">
                              <FontAwesomeIcon icon={faCheck} /> Activo
                            </span>
                          ) : (
                            <span className="badge badge--secondary font-bold d-inline-flex align-items-center gap-1">
                              <FontAwesomeIcon icon={faBan} /> Inactivo
                            </span>
                          )}
                        </td>
                        <td data-label="Acción" className="text-center" style={{ minWidth: '140px' }}>
                          <button
                            type="button"
                            className={`btn btn--xs ${conf.is_active ? 'btn--danger' : 'btn--success'} d-inline-flex align-items-center justify-content-center gap-1 font-bold w-full`}
                            style={{ whiteSpace: 'nowrap', padding: '6px 12px' }}
                            onClick={() => handleToggle(conf)}
                            disabled={isUpdating}
                            title={conf.is_active ? 'Desactivar esta configuración' : 'Activar esta configuración'}
                          >
                            {isUpdating ? (
                              <FontAwesomeIcon icon={faCircleNotch} spin />
                            ) : (
                              <FontAwesomeIcon icon={conf.is_active ? faToggleOn : faToggleOff} />
                            )}
                            <span>{conf.is_active ? 'Desactivar' : 'Activar'}</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Paginación estandarizada */}
          <div className="mt-3">
            <PaginationButtons
              onPrev={() => setPage((prev) => Math.max(0, prev - 1))}
              onNext={() => setPage((prev) => prev + 1)}
              canGoPrev={page > 0}
              canGoNext={hasMore}
              page={page}
            />
          </div>
        </div>

        <div className="modal__footer d-flex justify-content-between align-items-center flex-wrap gap-2">
          <small className="text-muted d-flex align-items-center gap-1">
            <FontAwesomeIcon icon={faInfoCircle} />
            <span>Los cambios en las banderas operacionales se aplican en tiempo real en pedidos, catálogo y almacén.</span>
          </small>
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
