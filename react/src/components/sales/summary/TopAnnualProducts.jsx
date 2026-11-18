import React, { useRef, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCalendarAlt, faChevronLeft, faChevronRight } from '@fortawesome/free-solid-svg-icons';
import { formatCurrency } from '../../../utils/formatUtils';

export default function TopAnnualProducts({
  topProducts,
  topYear,
  setTopYear,
  topSortBy,
  setTopSortBy,
  loadingTop,
  canViewProfits,
  currentSystemYear,
  isYearPickerOpen,
  setIsYearPickerOpen,
  pickerDecadeStart,
  setPickerDecadeStart
}) {
  const yearPickerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (yearPickerRef.current && !yearPickerRef.current.contains(event.target)) {
        setIsYearPickerOpen(false);
      }
    };
    if (isYearPickerOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isYearPickerOpen, setIsYearPickerOpen]);

  return (
    <div className="top-products-container">
      <div className="top-products-header">
        <div>
          <h4 className="top-products-title">
            <span>🏆</span> Productos Destacados del Año ({topYear})
          </h4>
          <span className="top-products-subtitle">
            Métricas acumuladas O(1)
          </span>
        </div>

        <div className="top-products-controls">
          <select
            className="select top-products-select"
            value={topSortBy}
            onChange={(e) => setTopSortBy(e.target.value)}
          >
            <option value="orders">🛒 Más Populares (N° Pedidos)</option>
            <option value="units">📦 Mayor Volumen (Piezas)</option>
            {canViewProfits && <option value="profit">💹 Mayor Ganancia ($)</option>}
            <option value="revenue">💰 Mayor Facturación ($)</option>
          </select>

          {/* CALENDARIO / PICKER DE AÑO DINÁMICO */}
          <div className="year-picker" ref={yearPickerRef}>
            <div className="year-picker__group">
              <button
                type="button"
                className="btn btn--sm btn--secondary year-picker__step year-picker__step--prev"
                onClick={() => setTopYear(y => y - 1)}
                title="Año anterior"
              >
                <FontAwesomeIcon icon={faChevronLeft} />
              </button>

              <button
                type="button"
                className="btn btn--sm btn--secondary year-picker__trigger"
                onClick={() => {
                  setPickerDecadeStart(Math.floor(topYear / 10) * 10);
                  setIsYearPickerOpen(!isYearPickerOpen);
                }}
                title="Abrir selector de año"
              >
                <FontAwesomeIcon icon={faCalendarAlt} className="icon-cal" />
                <span>Año {topYear}</span>
                <span className="icon-caret">▾</span>
              </button>

              <button
                type="button"
                className="btn btn--sm btn--secondary year-picker__step year-picker__step--next"
                onClick={() => setTopYear(y => y + 1)}
                title="Año siguiente"
              >
                <FontAwesomeIcon icon={faChevronRight} />
              </button>
            </div>

            {/* POPOVER CALENDARIO DE AÑOS */}
            {isYearPickerOpen && (
              <div className="year-picker__popover">
                <div className="year-picker__decade-nav">
                  <button
                    type="button"
                    className="btn btn--sm btn--ghost"
                    onClick={() => setPickerDecadeStart(d => d - 10)}
                    title="Década anterior"
                  >
                    <FontAwesomeIcon icon={faChevronLeft} />
                  </button>
                  <strong>
                    {pickerDecadeStart} – {pickerDecadeStart + 9}
                  </strong>
                  <button
                    type="button"
                    className="btn btn--sm btn--ghost"
                    onClick={() => setPickerDecadeStart(d => d + 10)}
                    title="Década siguiente"
                  >
                    <FontAwesomeIcon icon={faChevronRight} />
                  </button>
                </div>

                <div className="year-picker__grid">
                  {Array.from({ length: 10 }, (_, i) => pickerDecadeStart + i).map(year => {
                    const isSelected = year === topYear;
                    const isCurrent = year === currentSystemYear;
                    const btnCls = `year-picker__year-btn ${isSelected ? 'year-picker__year-btn--selected' : ''} ${isCurrent ? 'year-picker__year-btn--current' : ''}`;
                    return (
                      <button
                        key={year}
                        type="button"
                        className={btnCls.trim()}
                        onClick={() => {
                          setTopYear(year);
                          setIsYearPickerOpen(false);
                        }}
                      >
                        {year}
                      </button>
                    );
                  })}
                </div>

                <div className="year-picker__footer">
                  <button
                    type="button"
                    className="btn btn--sm btn--ghost"
                    onClick={() => {
                      setTopYear(currentSystemYear);
                      setIsYearPickerOpen(false);
                    }}
                  >
                    📅 Año Actual ({currentSystemYear})
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {loadingTop ? (
        <div className="top-products__empty">
          Cargando estadísticas anuales...
        </div>
      ) : topProducts.length === 0 ? (
        <p className="top-products__empty">
          No hay ventas registradas para el año {topYear}.
        </p>
      ) : (
        <div className="table-container top-products__table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th className="top-products__th-rank">#</th>
                <th>Producto</th>
                <th className="text-center">N° Pedidos</th>
                <th className="text-center">Unidades</th>
                <th className="text-right">Venta Total</th>
                {canViewProfits && <th className="text-right">Ganancia Neta</th>}
              </tr>
            </thead>
            <tbody>
              {topProducts.map((p, idx) => (
                <tr key={p.product_id}>
                  <td className="top-products__td-rank">
                    {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : idx + 1}
                  </td>
                  <td data-label="Producto">
                    <div>
                      <strong className="top-products__name">{p.name}</strong>
                      {p.codebar && (
                        <div className="top-products__codebar">
                          #{p.codebar}
                        </div>
                      )}
                    </div>
                  </td>
                  <td data-label="N° Pedidos" className="text-center">
                    <span className={`top-products__orders-badge ${topSortBy === 'orders' ? 'top-products__orders-badge--active' : ''}`}>
                      {p.orders_count} {p.orders_count === 1 ? 'pedido' : 'pedidos'}
                    </span>
                  </td>
                  <td data-label="Unidades" className="text-center">
                    <span className={`top-products__units-val ${topSortBy === 'units' ? 'top-products__units-val--active' : ''}`}>
                      {p.units_sold} {p.units_sold === 1 ? 'pza' : 'pzas'}
                    </span>
                  </td>
                  <td data-label="Venta Total" className="text-right">
                    <strong className={topSortBy === 'revenue' ? 'top-products__revenue-val--active' : ''}>
                      {formatCurrency(p.total_revenue)}
                    </strong>
                  </td>
                  {canViewProfits && (
                    <td data-label="Ganancia Neta" className="text-right">
                      <span className={p.total_profit < -0.001 ? 'text-danger font-bold' : 'text-success font-bold'}>
                        {p.total_profit < -0.001 ? formatCurrency(p.total_profit) : `+${formatCurrency(p.total_profit)}`}
                      </span>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
