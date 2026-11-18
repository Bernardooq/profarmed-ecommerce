import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faUserFriends, faUsers, faUserTie, faWarehouse, faBullhorn, faTruck
} from '@fortawesome/free-solid-svg-icons';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Cell } from 'recharts';

export const getRoleStatIcon = (slug = '') => {
  const s = String(slug || '').toLowerCase();
  if (s.includes('ware') || s.includes('almacen') || s.includes('bodega')) return faWarehouse;
  if (s.includes('market') || s.includes('difus') || s.includes('mercad')) return faBullhorn;
  if (s.includes('sell') || s.includes('vent') || s.includes('comerc')) return faUserTie;
  if (s.includes('repart') || s.includes('chofer') || s.includes('envio')) return faTruck;
  return faUserFriends;
};

export default function StaffCustomersSection({
  summary,
  showTitles,
  visibility,
  personalData,
  colors,
  CustomTooltip
}) {
  return (
    <div className="stat-group">
      {showTitles && (
        <h3 className="stat-group__title">
          <FontAwesomeIcon icon={faUserFriends} className="stat-group__icon" />{' '}
          {visibility.hasUsersPerm && visibility.hasCustomersPerm
            ? 'Personal y Clientes'
            : visibility.hasUsersPerm
              ? 'Personal Interno'
              : 'Cartera de Clientes'}
        </h3>
      )}
      <section className="stat-grid">
        {visibility.hasCustomersPerm && summary.total_customers !== undefined && (
          <div className="stat-card">
            <div className="stat-card__icon"><FontAwesomeIcon icon={faUsers} /></div>
            <div className="stat-card__content">
              <span className="stat-card__value">{summary.total_customers}</span>
              <span className="stat-card__label">Clientes Registrados</span>
            </div>
          </div>
        )}
        {visibility.hasUsersPerm && (
          Array.isArray(summary.roles_breakdown) && summary.roles_breakdown.length > 0 ? (
            summary.roles_breakdown
              .filter(r => r.slug !== 'admin')
              .map((r) => (
                <div className="stat-card" key={`role-card-${r.role_id || r.slug}`}>
                  <div className="stat-card__icon stat-card__icon--role">
                    <FontAwesomeIcon icon={getRoleStatIcon(r.slug)} />
                  </div>
                  <div className="stat-card__content">
                    <span className="stat-card__value">{r.count}</span>
                    <span className="stat-card__label">{r.name}</span>
                  </div>
                </div>
              ))
          ) : (
            summary.total_users !== undefined && (
              <div className="stat-card">
                <div className="stat-card__icon"><FontAwesomeIcon icon={faUserTie} /></div>
                <div className="stat-card__content">
                  <span className="stat-card__value">{summary.total_users}</span>
                  <span className="stat-card__label">Personal Interno</span>
                </div>
              </div>
            )
          )
        )}
      </section>

      {personalData.length > 0 && (
        <div className="stat-chart-box stat-chart-box--bar">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={personalData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke={colors.border} />
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: colors.text, fontSize: 12 }} width={80} />
              <RechartsTooltip content={CustomTooltip} cursor={{ fill: colors.border, opacity: 0.3 }} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                {personalData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
