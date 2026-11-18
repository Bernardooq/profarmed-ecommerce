import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEnvelope, faTrash, faCheck, faDownload, faSearch, faTimes } from '@fortawesome/free-solid-svg-icons';
import contactClientService from '../../services/contactClientService';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import PaginationButtons from '../common/PaginationButtons';
import { usePaginationLimit } from '../../context/PaginationLimitContext';

export default function ContactClientPanel({ refreshCounts }) {
  const { can } = usePermissions();
  const canManageContact = can(PERMISSIONS.CONTACT_MANAGE);
  const canManageRequests = can(PERMISSIONS.CUSTOMERS_REQUESTS_MANAGE);
  const canDownloadDocs = can(PERMISSIONS.CUSTOMERS_REQUESTS_DOWNLOAD);

  const [viewType, setViewType] = useState('messages'); // 'messages' or 'requests'
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filters and Pagination
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const { limit: itemsPerPage } = usePaginationLimit();

  useEffect(() => {
    loadData();
  }, [viewType, statusFilter, page, itemsPerPage]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        skip: page * itemsPerPage,
        limit: itemsPerPage + 1
      };
      if (searchTerm.trim() !== '') params.search = searchTerm;
      if (statusFilter !== 'all') {
        if (viewType === 'messages') {
          params.status_filter = statusFilter;
        } else {
          params.status = statusFilter;
        }
      }

      let response;
      if (viewType === 'messages') {
        response = await contactClientService.getContactMessages(params);
      } else {
        response = await contactClientService.getClientRequests(params);
      }

      const results = response || [];
      const hasMorePages = results.length > itemsPerPage;
      setHasMore(hasMorePages);
      setData(hasMorePages ? results.slice(0, itemsPerPage) : results);
      if (refreshCounts) refreshCounts();
    } catch (err) {
      setError(`No se pudieron cargar los datos de ${viewType === 'messages' ? 'mensajes' : 'solicitudes'}.`);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(0);
    loadData();
  };

  const handleUpdateContactStatus = async (id, currentStatus) => {
    try {
      const newStatus = currentStatus === 'pending' ? 'contacted' : 'pending';
      await contactClientService.updateContactStatus(id, newStatus);
      await loadData();
    } catch (err) {
      alert("Error al actualizar estado");
    }
  };

  const handleUpdateClientRequestStatus = async (id, newStatus) => {
    try {
      await contactClientService.updateClientRequestStatus(id, newStatus);
      await loadData();
    } catch (err) {
      alert("Error al actualizar estado de la solicitud");
    }
  };

  const handleDeleteContact = async (id) => {
    if (!window.confirm("¿Seguro que deseas eliminar este mensaje?")) return;
    try {
      await contactClientService.deleteContactMessage(id);
      await loadData();
    } catch (err) {
      alert("Error al eliminar mensaje");
    }
  };

  const handleDeleteRequest = async (id) => {
    if (!window.confirm("¿Seguro que deseas eliminar esta solicitud y sus documentos?")) return;
    try {
      await contactClientService.deleteClientRequest(id);
      await loadData();
    } catch (err) {
      alert("Error al eliminar solicitud");
    }
  };

  const handleDownloadDoc = async (id, docType) => {
    try {
      const response = await contactClientService.getClientRequestDocUrl(id, docType);
      if (response.download_url) {
        window.open(response.download_url, '_blank');
      }
    } catch (err) {
      alert("Error al generar enlace de descarga");
    }
  };

  if (error && data.length === 0 && !loading) {
    return (
      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">Mensajes y Solicitudes</h2>
        </div>
        <div className="empty-state">
          <p className="alert alert--danger">{error}</p>
          <button className="btn btn--primary btn--sm" onClick={() => loadData()}>
            Reintentar
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="dashboard-section">
      <div className="section-header">
        <h2 className="section-title">Mensajes y Solicitudes</h2>
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      <div className="dashboard-controls" style={{ flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button 
            type="button" 
            className={`btn ${viewType === 'messages' ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => {
              setViewType('messages');
              setSearchTerm('');
              setStatusFilter('all');
              setPage(0);
            }}
          >
            Mensajes de Contacto
          </button>
          <button 
            type="button" 
            className={`btn ${viewType === 'requests' ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => {
              setViewType('requests');
              setSearchTerm('');
              setStatusFilter('all');
              setPage(0);
            }}
          >
            Solicitudes "Ser Cliente"
          </button>
        </div>

        <form className="search-bar" onSubmit={handleSearch} style={{ flexGrow: 1 }}>
          <input 
            className="input" 
            type="search" 
            placeholder="Buscar por nombre, email o asunto..." 
            value={searchTerm} 
            onChange={(e) => setSearchTerm(e.target.value)} 
          />
          <button type="submit" className="btn btn--primary" aria-label="Buscar">
            <FontAwesomeIcon icon={faSearch} />
          </button>
        </form>

        <div className="filter-group">
          <label className="filter-group__label" htmlFor="filterStatus">Estado:</label>
          <select 
            className="select" 
            id="filterStatus" 
            value={statusFilter} 
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
          >
            <option value="all">Todos</option>
            <option value="pending">Pendientes</option>
            {viewType === 'messages' ? (
              <option value="contacted">Contactados</option>
            ) : (
              <>
                <option value="approved">Aprobados</option>
                <option value="rejected">Rechazados</option>
              </>
            )}
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Cargando datos..." />
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                {viewType === 'messages' ? (
                  <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Contacto</th>
                    <th>Asunto</th>
                    <th>Mensaje</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                ) : (
                  <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Contacto</th>
                    <th>Asunto</th>
                    <th>Mensaje</th>
                    <th>Documentos PDF</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {data.length === 0 ? (
                  <tr>
                    <td colSpan={viewType === 'messages' ? 7 : 8} className="text-center py-8">No se encontraron registros</td>
                  </tr>
                ) : (
                  data.map((item) => (
                    <tr key={item.id}>
                      <td>#{item.id}</td>
                      <td>{item.full_name}</td>
                      <td>
                        <div><FontAwesomeIcon icon={faEnvelope} /> {item.email}</div>
                        <div>{item.phone}</div>
                      </td>
                      <td>{item.subject}</td>
                      
                      {viewType === 'messages' ? (
                        <td style={{ maxWidth: '300px', whiteSpace: 'normal' }}>
                          <small>{item.message}</small>
                        </td>
                      ) : (
                        <>
                          <td style={{ maxWidth: '300px', whiteSpace: 'normal' }}>
                            <small>{item.message || <em className="text-muted">Sin comentarios</em>}</small>
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                              <button 
                                className="btn btn--secondary btn--sm" 
                                onClick={() => handleDownloadDoc(item.id, 'id')} 
                                title="Identificación"
                                disabled={!canDownloadDocs}
                              >
                                <FontAwesomeIcon icon={faDownload} /> Identificación
                              </button>
                              <button 
                                className="btn btn--secondary btn--sm" 
                                onClick={() => handleDownloadDoc(item.id, 'sanitary')} 
                                title="Aviso de Funcionamiento"
                                disabled={!canDownloadDocs}
                              >
                                <FontAwesomeIcon icon={faDownload} /> Aviso Func.
                              </button>
                              <button 
                                className="btn btn--secondary btn--sm" 
                                onClick={() => handleDownloadDoc(item.id, 'address')} 
                                title="Comprobante de Domicilio"
                                disabled={!canDownloadDocs}
                              >
                                <FontAwesomeIcon icon={faDownload} /> Domicilio
                              </button>
                              <button 
                                className="btn btn--secondary btn--sm" 
                                onClick={() => handleDownloadDoc(item.id, 'tax')} 
                                title="Constancia de Situación Fiscal"
                                disabled={!canDownloadDocs}
                              >
                                <FontAwesomeIcon icon={faDownload} /> Constancia Fiscal
                              </button>
                            </div>
                          </td>
                        </>
                      )}

                      <td>
                        {viewType === 'messages' ? (
                          <span className={`badge ${item.status === 'pending' ? 'badge--warning' : 'badge--success'}`}>
                            {item.status === 'pending' ? 'Pendiente' : 'Contactado'}
                          </span>
                        ) : (
                          <span className={`badge ${
                            item.status === 'approved' ? 'badge--success' : 
                            item.status === 'rejected' ? 'badge--danger' : 'badge--warning'
                          }`}>
                            {item.status === 'approved' ? 'Aprobado' : 
                             item.status === 'rejected' ? 'Rechazado' : 'Pendiente'}
                          </span>
                        )}
                      </td>
                      
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          {viewType === 'messages' ? (
                            <>
                              {canManageContact && (
                                <button 
                                  className={`btn ${item.status === 'pending' ? 'btn--primary' : 'btn--secondary'} btn--sm`} 
                                  onClick={() => handleUpdateContactStatus(item.id, item.status)}
                                  title="Cambiar estado"
                                >
                                  <FontAwesomeIcon icon={faCheck} />
                                </button>
                              )}
                              {canManageContact && (
                                <button 
                                  className="btn btn--danger btn--sm" 
                                  onClick={() => handleDeleteContact(item.id)}
                                  title="Eliminar mensaje"
                                >
                                  <FontAwesomeIcon icon={faTrash} />
                                </button>
                              )}
                            </>
                          ) : (
                            <>
                              {canManageRequests && (
                                <button 
                                  className={`btn ${item.status === 'approved' ? 'btn--secondary' : 'btn--primary'} btn--sm`}
                                  onClick={() => handleUpdateClientRequestStatus(item.id, 'approved')}
                                  title="Aprobar solicitud"
                                  style={{ backgroundColor: item.status !== 'approved' ? 'var(--color-success)' : undefined, color: 'var(--color-text-white)' }}
                                >
                                  <FontAwesomeIcon icon={faCheck} />
                                </button>
                              )}
                              {canManageRequests && (
                                <button 
                                  className={`btn ${item.status === 'rejected' ? 'btn--secondary' : 'btn--primary'} btn--sm`}
                                  onClick={() => handleUpdateClientRequestStatus(item.id, 'rejected')}
                                  title="Rechazar solicitud"
                                  style={{ backgroundColor: item.status !== 'rejected' ? 'var(--color-danger)' : undefined, color: 'var(--color-text-white)' }}
                                >
                                  <FontAwesomeIcon icon={faTimes} />
                                </button>
                              )}
                              {canManageRequests && (
                                <button 
                                  className="btn btn--danger btn--sm" 
                                  onClick={() => handleDeleteRequest(item.id)}
                                  title="Eliminar solicitud"
                                >
                                  <FontAwesomeIcon icon={faTrash} />
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {data.length > 0 && (
            <PaginationButtons
              onPrev={() => setPage(p => Math.max(0, p - 1))}
              onNext={() => setPage(p => p + 1)}
              canGoPrev={page > 0}
              canGoNext={hasMore}
            />
          )}
        </>
      )}
    </section>
  );
}
