import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faWarehouse, faBoxOpen, faExclamationCircle, faExclamationTriangle
} from '@fortawesome/free-solid-svg-icons';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip as RechartsTooltip, Legend } from 'recharts';

export default function InventoryStatSection({
  summary,
  showTitles,
  inventarioData,
  colors,
  CustomTooltip
}) {
  return (
    <div className="stat-group">
      {showTitles && (
        <h3 className="stat-group__title">
          <FontAwesomeIcon icon={faWarehouse} className="stat-group__icon" /> Inventario
        </h3>
      )}
      <section className="stat-grid">
        <div className="stat-card">
          <div className="stat-card__icon"><FontAwesomeIcon icon={faBoxOpen} /></div>
          <div className="stat-card__content">
            <span className="stat-card__value">{summary.total_products || summary.catalogCount || 0}</span>
            <span className="stat-card__label">Productos en Catálogo</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__icon stat-card__icon--warning"><FontAwesomeIcon icon={faExclamationCircle} /></div>
          <div className="stat-card__content">
            <span className="stat-card__value">{summary.low_stock_count || summary.lowStockCount || 0}</span>
            <span className="stat-card__label">Productos con Bajo Stock</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__icon stat-card__icon--danger"><FontAwesomeIcon icon={faExclamationTriangle} /></div>
          <div className="stat-card__content">
            <span className="stat-card__value">{summary.out_of_stock_count || summary.outOfStockCount || 0}</span>
            <span className="stat-card__label">Productos Agotados</span>
          </div>
        </div>
      </section>

      {inventarioData.length > 0 && (
        <div className="stat-chart-box stat-chart-box--inventory">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={inventarioData}
                cx="50%"
                cy="38%"
                outerRadius={65}
                dataKey="value"
                stroke={colors.surface}
                strokeWidth={2}
              >
                {inventarioData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
              </Pie>
              <RechartsTooltip content={CustomTooltip} />
              <Legend
                iconType="circle"
                verticalAlign="bottom"
                wrapperStyle={{
                  paddingTop: '8px',
                  bottom: '4px',
                  width: '100%'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
