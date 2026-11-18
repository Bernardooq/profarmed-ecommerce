import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlus, faTrash, faEdit, faSearch, faEye, faPaperPlane } from '@fortawesome/free-solid-svg-icons';
import announcementService from '../../services/announcementService';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import PaginationButtons from '../common/PaginationButtons';
import { usePaginationLimit } from '../../context/PaginationLimitContext';
import StoryViewerModal from '../announcements/StoryViewerModal';
import ShareAnnouncementModal, { WhatsAppIcon } from '../announcements/ShareAnnouncementModal';
import ModalAnnouncementForm from '../announcements/ModalAnnouncementForm';

export default function AnnouncementsPanel() {
  const { can } = usePermissions();
  const canCreate = can(PERMISSIONS.ANNOUNCEMENTS_CREATE);
  const canEdit = can(PERMISSIONS.ANNOUNCEMENTS_EDIT);
  const canDelete = can(PERMISSIONS.ANNOUNCEMENTS_DELETE);
  const canBroadcast = can(PERMISSIONS.ANNOUNCEMENTS_BROADCAST);
  const canUpload = can(PERMISSIONS.ANNOUNCEMENTS_UPLOAD);

  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters and Pagination
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const { limit: itemsPerPage } = usePaginationLimit();

  // Modal State
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [previewItem, setPreviewItem] = useState(null);
  const [shareItem, setShareItem] = useState(null);
  const [editingItem, setEditingItem] = useState(null);

  useEffect(() => {
    loadData();
  }, [statusFilter, typeFilter, page, itemsPerPage]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        skip: page * itemsPerPage,
        limit: itemsPerPage + 1
      };

      const response = await announcementService.getAnnouncements(params);
      let results = response || [];

      if (searchTerm.trim() !== '') {
        results = results.filter(a => a.title.toLowerCase().includes(searchTerm.toLowerCase()));
      }
      if (statusFilter !== 'all') {
        results = results.filter(a => a.status === statusFilter);
      }
      if (typeFilter !== 'all') {
        results = results.filter(a => a.type === typeFilter);
      }

      const hasMorePages = results.length > itemsPerPage;
      setHasMore(hasMorePages);
      setData(hasMorePages ? results.slice(0, itemsPerPage) : results);
    } catch (err) {
      setError("No se pudieron cargar los anuncios.");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(0);
    loadData();
  };

  const handleDelete = async (id) => {
    if (!window.confirm("¿Seguro que deseas eliminar este anuncio?")) return;
    try {
      await announcementService.deleteAnnouncement(id);
      await loadData();
    } catch (err) {
      alert("Error al eliminar anuncio");
    }
  };

  const handleSendEmail = async (item) => {
    if (!window.confirm(`¿Seguro que deseas enviar el anuncio "${item.title}" por correo a todos los clientes que tengan notificaciones activadas?`)) return;
    try {
      setLoading(true);
      const res = await announcementService.sendAnnouncement(item.id);
      alert(res.message || "Correos enviados exitosamente.");
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || "Error al enviar correos");
    } finally {
      setLoading(false);
    }
  };

  const openForm = (item = null) => {
    setEditingItem(item);
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    setEditingItem(null);
  };

  return (
    <section className="dashboard-section">
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="section-title">Anuncios y Promos</h2>
        {canCreate && (
          <button className="btn btn--primary" onClick={() => openForm()}>
            <FontAwesomeIcon icon={faPlus} /> Añadir Anuncio
          </button>
        )}
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      <div className="dashboard-controls">
        <div className="filter-group">
          <label className="filter-group__label" htmlFor="filterType">Tipo:</label>
          <select
            className="select"
            id="filterType"
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(0);
            }}
          >
            <option value="all">Todos</option>
            <option value="popup">Pop-up</option>
            <option value="story">Story</option>
            <option value="footer">Footer Banner</option>
          </select>
        </div>

        <form onSubmit={handleSearch} className="search-form">
          <input
            className="input"
            type="search"
            placeholder="Buscar por título..."
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
            <option value="activo">Activos</option>
            <option value="inactivo">Inactivos</option>
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Cargando anuncios..." />
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Título</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                  <th>Fecha Inicio</th>
                  <th>Fecha Fin</th>
                  <th>Último Envío</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {data.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="text-center py-8">No se encontraron anuncios</td>
                  </tr>
                ) : (
                  data.map((item) => (
                    <tr key={item.id}>
                      <td>#{item.id}</td>
                      <td style={{ fontWeight: '500' }}>{item.title}</td>
                      <td>
                        <span className="badge badge--secondary" style={{ textTransform: 'capitalize' }}>
                          {item.type}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${item.status === 'activo' ? 'badge--success' : 'badge--danger'}`}>
                          {item.status}
                        </span>
                      </td>
                      <td>{new Date(item.start_date).toLocaleDateString()}</td>
                      <td>{item.end_date ? new Date(item.end_date).toLocaleDateString() : 'Indefinido'}</td>
                      <td>{item.last_send ? new Date(item.last_send).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' }) : 'Nunca enviado'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button className="btn btn--primary btn--sm" onClick={() => setPreviewItem(item)} title="Previsualizar">
                            <FontAwesomeIcon icon={faEye} />
                          </button>
                          <button
                            type="button"
                            className="btn btn--whatsapp btn--sm"
                            onClick={() => setShareItem(item)}
                            title="Compartir por WhatsApp"
                            aria-label={`Compartir ${item.title} por WhatsApp`}
                          >
                            <WhatsAppIcon />
                          </button>
                          {canEdit && (
                            <button className="btn btn--secondary btn--sm" onClick={() => openForm(item)} title="Editar">
                              <FontAwesomeIcon icon={faEdit} />
                            </button>
                          )}
                          {canBroadcast && (
                            <button
                              className="btn btn--success btn--sm"
                              onClick={() => handleSendEmail(item)}
                              title="Enviar por Correo a Clientes"
                            >
                              <FontAwesomeIcon icon={faPaperPlane} />
                            </button>
                          )}
                          {canDelete && (
                            <button className="btn btn--danger btn--sm" onClick={() => handleDelete(item.id)} title="Eliminar">
                              <FontAwesomeIcon icon={faTrash} />
                            </button>
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

      <ModalAnnouncementForm
        isOpen={isFormOpen}
        onClose={closeForm}
        onSaved={loadData}
        editingItem={editingItem}
        canUpload={canUpload}
      />

      {/* MODAL DE PREVISUALIZACIÓN */}
      {previewItem && previewItem.type === 'story' ? (
        <StoryViewerModal
          story={previewItem}
          onClose={() => setPreviewItem(null)}
          duration={6000}
        />
      ) : previewItem ? (
        <div className="popup-overlay" onClick={() => setPreviewItem(null)} style={{ zIndex: 10005, background: 'rgba(0,0,0,0.8)' }}>

          {previewItem.type === 'popup' && (
            <div className="popup-content" onClick={e => e.stopPropagation()}>
              <button className="close-btn" onClick={() => setPreviewItem(null)}>&times;</button>
              <h2>{previewItem.title}</h2>
              {previewItem.content && <p>{previewItem.content}</p>}
              {previewItem.img_url && <img src={previewItem.img_url} alt={previewItem.title} />}
            </div>
          )}

          {previewItem.type === 'footer' && (
            <div className="footer-banner" onClick={e => e.stopPropagation()} style={{ zIndex: 10006 }}>
              <div className="banner-content">
                {previewItem.img_url && <img src={previewItem.img_url} alt={previewItem.title} />}
                <div>
                  <h4>{previewItem.title}</h4>
                  {previewItem.content && <p>{previewItem.content}</p>}
                </div>
              </div>
              <button className="close-btn" onClick={() => setPreviewItem(null)}>&times;</button>
            </div>
          )}

        </div>
      ) : null}
      <ShareAnnouncementModal item={shareItem} onClose={() => setShareItem(null)} />
    </section>
  );
}
