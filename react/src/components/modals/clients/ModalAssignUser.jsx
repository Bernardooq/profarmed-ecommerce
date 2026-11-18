import { useState, useEffect, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faSearch, faUserCheck } from '@fortawesome/free-solid-svg-icons';
import salesGroupService from '../../../services/salesGroupService';
import { userService } from '../../../services/userService';
import { usePermissions } from '../../../hooks/usePermissions';
import PaginationButtons from '../../common/PaginationButtons';

const DEBOUNCE_MS = 1000;
const PAGE_SIZE = 50;

export default function ModalAssignUser({ visible, order, groupId, onAssign, onClose }) {
    const { user: currentUser, isAdmin } = usePermissions();
    const [selectedUserId, setSelectedUserId] = useState('');
    const [users, setUsers] = useState([]);
    const [usersLoading, setUsersLoading] = useState(false);
    const [usersError, setUsersError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [skip, setSkip] = useState(0);
    const [hasMore, setHasMore] = useState(false);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Reset when modal opens
    useEffect(() => {
        if (visible) {
            setSelectedUserId('');
            setError(null);
            setSearchTerm('');
            setDebouncedSearch('');
            setSkip(0);
        }
    }, [visible]);

    // Debounce search input (Typing)
    useEffect(() => {
        const t = setTimeout(() => {
            setDebouncedSearch(searchTerm);
            setSkip(0);
        }, 2500); // 2.5s debounce
        return () => clearTimeout(t);
    }, [searchTerm]);

    const handleSearch = (e) => {
        if (e) e.preventDefault();
        setDebouncedSearch(searchTerm);
        setSkip(0);
    };

    // Load users whenever groupId, debouncedSearch or skip changes
    const loadUsers = useCallback(async () => {
        if (!visible) return;
        setUsersLoading(true);
        setUsersError(null);
        try {
            const params = { skip, limit: PAGE_SIZE + 1 };
            if (debouncedSearch) params.search = debouncedSearch;
            let data = [];
            if (groupId) {
                data = await salesGroupService.getUsersByGroup(groupId, params);
            } else {
                data = await userService.getUsers(params);
            }
            const more = data.length > PAGE_SIZE;
            setHasMore(more);
            setUsers(more ? data.slice(0, PAGE_SIZE) : data);
        } catch (err) {
            setUsersError('Error al cargar asesores o usuarios. Intenta de nuevo.');
            console.error(err);
        } finally {
            setUsersLoading(false);
        }
    }, [groupId, debouncedSearch, skip, visible]);

    useEffect(() => { loadUsers(); }, [loadUsers]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!selectedUserId) { setError('Debe seleccionar un asesor o usuario'); return; }
        setLoading(true); setError(null);
        try { await onAssign(parseInt(selectedUserId), ''); onClose(); }
        catch (err) { setError(err.message || 'Error al asignar asesor'); }
        finally { setLoading(false); }
    };

    if (!visible) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
                <div className="modal__header">
                    <h2>Asignar Asesor / Usuario</h2>
                    <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">&times;</button>
                </div>
                <div className="modal__body">
                    <p className="text-muted mb-4">
                        <strong>Pedido:</strong> #{order?.order_id}<br />
                        <strong>Cliente:</strong> {order?.customer?.full_name || order?.customer?.username}
                        {!groupId && (
                            <span className="d-block text-warning text-xs mt-1">
                                ⚠️ Cliente sin grupo asignado (asignación libre entre colaboradores internos).
                            </span>
                        )}
                    </p>

                    {error && <div className="alert alert--danger">{error}</div>}

                    {/* Búsqueda de usuario / asesor */}
                    <div className="form-group mb-3">
                        <label className="form-group__label" htmlFor="user-assign-search">
                            Buscar asesor o usuario comercial
                        </label>
                        <form className="search-bar" onSubmit={handleSearch}>
                            <input
                                id="user-assign-search"
                                className="input"
                                type="search"
                                placeholder="Nombre o usuario..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                autoFocus
                            />
                            <button type="submit" className="btn btn--primary" aria-label="Buscar" disabled={usersLoading}>
                                <FontAwesomeIcon icon={faSearch} />
                            </button>
                            {usersLoading && <FontAwesomeIcon icon={faSpinner} spin className="search-bar__spinner" />}
                        </form>
                    </div>

                    {usersError && <p className="text-danger text-sm mb-2">{usersError}</p>}

                    <form onSubmit={handleSubmit} className="modal__form">
                        <div className="form-group">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                                <label className="form-group__label mb-0" htmlFor="user-select">
                                    Seleccionar Asesor / Usuario Comercial *
                                    {users.length > 0 && (
                                        <span className="form-group__hint ms-2" style={{ fontWeight: 400 }}>
                                            ({users.length}{hasMore ? '+' : ''} resultados)
                                        </span>
                                    )}
                                </label>
                                {currentUser && !isAdmin && (
                                    <button
                                        type="button"
                                        className="btn btn--xs btn--ghost text-primary"
                                        onClick={() => setSelectedUserId(String(currentUser.user_id))}
                                        title="Asignar este pedido a mi usuario comercial"
                                    >
                                        <FontAwesomeIcon icon={faUserCheck} /> Asignármelo a mí
                                    </button>
                                )}
                            </div>

                            {users.length === 0 && !usersLoading ? (
                                <p className="text-muted text-sm">
                                    {debouncedSearch
                                        ? `Sin resultados para "${debouncedSearch}"`
                                        : (groupId ? 'No hay usuarios o asesores disponibles en este grupo.' : 'No hay colaboradores internos disponibles.')}
                                </p>
                            ) : (
                                <select
                                    className="select"
                                    id="user-select"
                                    value={selectedUserId}
                                    onChange={(e) => setSelectedUserId(e.target.value)}
                                    required
                                    size={Math.min(8, Math.max(users.length + 1, 3))}
                                >
                                    <option value="">-- Seleccione un asesor o usuario --</option>
                                    {users.map(u => (
                                        <option key={u.user_id} value={u.user_id}>
                                            {u.full_name} ({u.role_name || u.role_slug || u.role || u.username})
                                        </option>
                                    ))}
                                </select>
                            )}

                            {/* Paginación */}
                            {(skip > 0 || hasMore) && (
                                <div className="mt-2">
                                    <PaginationButtons
                                        onPrev={() => setSkip(s => Math.max(0, s - PAGE_SIZE))}
                                        onNext={() => setSkip(s => s + PAGE_SIZE)}
                                        canGoPrev={skip > 0 && !usersLoading}
                                        canGoNext={hasMore && !usersLoading}
                                    />
                                </div>
                            )}
                        </div>

                        <div className="modal__footer">
                            <button type="button" className="btn btn--secondary" onClick={onClose} disabled={loading}>Cancelar</button>
                            <button type="submit" className="btn btn--primary" disabled={loading || !selectedUserId}>
                                {loading ? (<><FontAwesomeIcon icon={faSpinner} spin /> Asignando...</>) : 'Asignar'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
