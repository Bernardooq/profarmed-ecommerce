import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch } from '@fortawesome/free-solid-svg-icons';

export default function DiscountsFilterBar({
  searchTerm,
  setSearchTerm,
  filterScope,
  setFilterScope,
  filterActive,
  setFilterActive,
  setPage
}) {
  return (
    <div className="discounts-manager__filters">
      <div className="discounts-manager__search-box">
        <input
          type="text"
          className="input"
          placeholder="Buscar por producto o descripción..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <FontAwesomeIcon icon={faSearch} className="search-icon" />
      </div>

      <div className="discounts-manager__select-group">
        <select
          className="input"
          value={filterScope}
          onChange={(e) => setFilterScope(e.target.value)}
        >
          <option value="all">Todos los Ámbitos</option>
          <option value="general">Solo Generales (Base)</option>
          <option value="price_list">Por Lista de Precios</option>
        </select>

        <select
          className="input"
          value={filterActive}
          onChange={(e) => {
            setFilterActive(e.target.value);
            if (setPage) setPage(0);
          }}
        >
          <option value="all">Todos los Estados</option>
          <option value="vigente">Solo Vigentes (Activos en fecha)</option>
          <option value="active">Activos (Interruptor ON)</option>
          <option value="inactive">Inactivos (Interruptor OFF)</option>
        </select>
      </div>
    </div>
  );
}
