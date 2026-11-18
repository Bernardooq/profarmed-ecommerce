import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faBox, faInbox, faClipboardCheck, faTruck, faCheckCircle, faTimesCircle
} from '@fortawesome/free-solid-svg-icons';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip as RechartsTooltip, Legend } from 'recharts';

export default function OrdersStatSection({
  summary,
  showTitles,
  pedidosData,
  colors,
  CustomTooltip
}) {
  return (
    <div className="stat-group">
      {showTitles && (
        <h3 className="stat-group__title">
          <FontAwesomeIcon icon={faBox} className="stat-group__icon" /> Gestión de Pedidos
        </h3>
      )}
      <section className="stat-grid">
        {summary.pending_orders !== undefined && (
          <div className="stat-card">
            <div className="stat-card__icon"><FontAwesomeIcon icon={faInbox} /></div>
            <div className="stat-card__content">
              <span className="stat-card__value">{summary.pending_orders || summary.pendingOrders || 0}</span>
              <span className="stat-card__label">Pedidos Pendientes</span>
            </div>
          </div>
        )}
        {summary.approved_orders !== undefined && (
          <div className="stat-card">
            <div className="stat-card__icon stat-card__icon--success"><FontAwesomeIcon icon={faClipboardCheck} /></div>
            <div className="stat-card__content">
              <span className="stat-card__value">{summary.approved_orders}</span>
              <span className="stat-card__label">Pedidos Aprobados</span>
            </div>
          </div>
        )}
        {summary.shipped_orders !== undefined && (
          <div className="stat-card">
            <div className="stat-card__icon stat-card__icon--info"><FontAwesomeIcon icon={faTruck} /></div>
            <div className="stat-card__content">
              <span className="stat-card__value">{summary.shipped_orders}</span>
              <span className="stat-card__label">Pedidos Enviados</span>
            </div>
          </div>
        )}
        {summary.delivered_orders !== undefined && (
          <div className="stat-card">
            <div className="stat-card__icon"><FontAwesomeIcon icon={faCheckCircle} /></div>
            <div className="stat-card__content">
              <span className="stat-card__value">{summary.delivered_orders}</span>
              <span className="stat-card__label">Pedidos Entregados</span>
            </div>
          </div>
        )}
        {summary.cancelled_orders !== undefined && (
          <div className="stat-card">
            <div className="stat-card__icon stat-card__icon--danger"><FontAwesomeIcon icon={faTimesCircle} /></div>
            <div className="stat-card__content">
              <span className="stat-card__value">{summary.cancelled_orders}</span>
              <span className="stat-card__label">Pedidos Cancelados</span>
            </div>
          </div>
        )}
      </section>

      {pedidosData.length > 0 && (
        <div className="stat-chart-box stat-chart-box--pie">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pedidosData}
                cx="50%"
                cy="38%"
                innerRadius={36}
                outerRadius={65}
                paddingAngle={2}
                dataKey="value"
                stroke="none"
              >
                {pedidosData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
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
