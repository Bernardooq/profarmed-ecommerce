import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch } from '@fortawesome/free-solid-svg-icons';
import customerService from '../../../services/customerService';
import salesGroupService from '../../../services/salesGroupService';
import LoadingSpinner from '../../common/LoadingSpinner';
import usePermissions from '../../../hooks/usePermissions';
import { PERMISSIONS } from '../../../config/permissions';

const CUSTOMERS_PER_PAGE = 10;

export default function CustomerSelector({ onSelect, visible }) {
    const { can, isAdmin } = usePermissions();
    const canManageAllCustomers = isAdmin || can(PERMISSIONS.CUSTOMERS_MANAGE);
    const isRestrictedToGroups = !canManageAllCustomers && can(PERMISSIONS.ORDERS_CREATE);

    const [customers, setCustomers] = useState([]);
    const [customerSearch, setCustomerSearch] = useState('');
    const [customersLoading, setCustomersLoading] = useState(false);
    const [customersPage, setCustomersPage] = useState(0);
    const [hasMoreCustomers, setHasMoreCustomers] = useState(true);

    // State de grupos asignados
    const [assignedGroups, setAssignedGroups] = useState([]);
    const [selectedGroupId, setSelectedGroupId] = useState(null);
    const [groupsLoading, setGroupsLoading] = useState(false);

    // Cargar grupos asignados al montar si tiene restricción
    useEffect(() => {
        if (visible && isRestrictedToGroups) {
            loadAssignedGroups();
        }
    }, [visible, isRestrictedToGroups]);

    // 1. Initial/Simple Load Effect (Immediate)
    // Triggers on page change, group change, or visibility
    useEffect(() => {
        if (visible) {
            // Load immediately for pagination/group changes
            if (isRestrictedToGroups) {
                if (selectedGroupId) loadAssignedGroupCustomers();
            } else {
                loadCustomers();
            }
        }
    }, [visible, customersPage, selectedGroupId, isRestrictedToGroups]);

    // 2. Search Load Effect (Debounced)
    // Only triggers when typing in customerSearch
    useEffect(() => {
        if (!customerSearch) return; // Resetting search is handled by the immediate effect above if user clears it

        const timer = setTimeout(() => {
            if (visible) {
                if (isRestrictedToGroups) {
                    if (selectedGroupId) loadAssignedGroupCustomers();
                } else {
                    loadCustomers();
                }
            }
        }, 2500); // 2500ms debounce for typing
        return () => clearTimeout(timer);
    }, [customerSearch, visible, isRestrictedToGroups]);

    const loadAssignedGroups = async () => {
        try {
            setGroupsLoading(true);
            const data = await salesGroupService.getMyGroups();
            setAssignedGroups(data);
            // Auto-select if only one group
            if (data.length === 1) {
                setSelectedGroupId(data[0].sales_group_id);
            }
        } catch (err) {
            console.error('Error loading assigned groups:', err);
            setAssignedGroups([]);
        } finally {
            setGroupsLoading(false);
        }
    };

    const loadAssignedGroupCustomers = async () => {
        if (!selectedGroupId) return;
        try {
            setCustomersLoading(true);
            const params = { skip: customersPage * CUSTOMERS_PER_PAGE, limit: CUSTOMERS_PER_PAGE + 1 };
            if (customerSearch) params.search = customerSearch;
            const data = await salesGroupService.getGroupCustomers(selectedGroupId, params);
            const hasMorePages = data.length > CUSTOMERS_PER_PAGE;
            setHasMoreCustomers(hasMorePages);
            setCustomers(hasMorePages ? data.slice(0, CUSTOMERS_PER_PAGE) : data);
        } catch (err) { console.error(err); setCustomers([]); }
        finally { setCustomersLoading(false); }
    };

    const loadCustomers = async () => {
        try {
            setCustomersLoading(true);
            const params = { skip: customersPage * CUSTOMERS_PER_PAGE, limit: CUSTOMERS_PER_PAGE + 1 };
            if (customerSearch) params.search = customerSearch;
            const data = await customerService.getAllCustomers(params);
            const hasMorePages = data.length > CUSTOMERS_PER_PAGE;
            setHasMoreCustomers(hasMorePages);
            setCustomers(hasMorePages ? data.slice(0, CUSTOMERS_PER_PAGE) : data);
        } catch (err) { console.error(err); setCustomers([]); }
        finally { setCustomersLoading(false); }
    };

    const handleCustomerSearch = (e) => {
        e.preventDefault();
        setCustomersPage(0);
        if (isRestrictedToGroups) {
            loadAssignedGroupCustomers();
        } else {
            loadCustomers();
        }
    };

    const handleGroupChange = (e) => {
        const groupId = parseInt(e.target.value);
        setSelectedGroupId(groupId);
        setCustomersPage(0);
        setCustomerSearch('');
        setCustomers([]);
    };

    return (
        <div>
            <h3 className="mb-3">Seleccionar Cliente</h3>

            {/* Grupo de Ventas asignado selector */}
            {isRestrictedToGroups && (
                <div className="mb-3">
                    {groupsLoading ? (
                        <LoadingSpinner message="Cargando grupos..." />
                    ) : assignedGroups.length === 0 ? (
                        <p className="text-center text-muted py-4">No tienes grupos comerciales asignados</p>
                    ) : assignedGroups.length > 1 ? (
                        <div className="form-group">
                            <label className="form-group__label" htmlFor="sales-group-select">Grupo Comercial:</label>
                            <select
                                id="sales-group-select"
                                className="select"
                                value={selectedGroupId || ''}
                                onChange={handleGroupChange}
                            >
                                <option value="" disabled>Selecciona un grupo</option>
                                {assignedGroups.map(g => (
                                    <option key={g.sales_group_id} value={g.sales_group_id}>
                                        {g.group_name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    ) : null}
                </div>
            )}

            {/* Show search bar and customer list only when ready */}
            {(!isRestrictedToGroups || selectedGroupId) && (
                <>
                    <form className="search-bar mb-3" onSubmit={handleCustomerSearch}>
                        <input 
                            className="input" 
                            type="search" 
                            placeholder="Buscar cliente por nombre, email, RFC o ID..." 
                            value={customerSearch} 
                            onChange={(e) => setCustomerSearch(e.target.value)} 
                            // Removed disabled={customersLoading} to keep the mobile keyboard open
                        />
                        <button className="btn btn--primary" type="submit" aria-label="Buscar" disabled={customersLoading}>
                            <FontAwesomeIcon icon={faSearch} />
                        </button>
                    </form>

                    {customersLoading ? (
                        <LoadingSpinner message="Cargando clientes..." />
                    ) : customers.length === 0 ? (
                        <p className="text-center text-muted py-4">No se encontraron clientes</p>
                    ) : (
                        <div className="customer-select-list">
                            {customers.map((customer) => (
                                <button
                                    key={customer.customer_id}
                                    type="button"
                                    className="customer-select-list__item"
                                    onClick={() => onSelect(customer)}
                                >
                                    <span className="customer-select-list__id">{customer.customer_id}</span>
                                    <span className="customer-select-list__info">
                                        <strong>{customer.full_name}</strong>
                                        <span className="customer-select-list__email">{customer.email}</span>
                                        {customer.rfc && (
                                            <span className="customer-select-list__rfc">
                                                RFC: {customer.rfc}
                                            </span>
                                        )}
                                    </span>
                                </button>
                            ))}
                        </div>
                    )}

                    {!customersLoading && customers.length > 0 && (
                        <div className="d-flex justify-center gap-2 mt-3">
                            <button type="button" className="btn btn--secondary" onClick={() => setCustomersPage(p => Math.max(0, p - 1))} disabled={customersPage === 0}>Anterior</button>
                            <button type="button" className="btn btn--secondary" onClick={() => setCustomersPage(p => p + 1)} disabled={!hasMoreCustomers}>Siguiente</button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
