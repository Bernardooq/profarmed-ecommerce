import React from 'react';
import { formatCurrency } from '../../../utils/formatUtils';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, Cell } from 'recharts';

export default function SalesTrendChart({
  salesPeriod,
  setSalesPeriod,
  salesChartData,
  periodTotals,
  canViewProfits,
  loadingSales,
  colors,
  CustomTooltip
}) {
  return (
    <div className="sales-trend-box">
      <div className="sales-trend-box__header">
        <div>
          <h4 className="sales-trend-box__title">Tendencia de Ventas</h4>
          {salesChartData.length > 0 && (
            <div className="sales-trend-box__stats">
              <span className="text-muted">
                Ventas Periodo: <strong className="text-info">{formatCurrency(periodTotals.ventas)}</strong>
              </span>
              {canViewProfits && (
                <span className="text-muted">
                  Ganancia Periodo:{' '}
                  <strong className={periodTotals.ganancia < -0.001 ? 'text-danger' : 'text-success'}>
                    {periodTotals.ganancia < -0.001 ? formatCurrency(periodTotals.ganancia) : `+${formatCurrency(periodTotals.ganancia)}`}
                  </strong>
                </span>
              )}
            </div>
          )}
        </div>
        <select
          className="input sales-trend-box__select"
          value={salesPeriod}
          onChange={(e) => setSalesPeriod(e.target.value)}
        >
          <option value="weekly">Última Semana</option>
          <option value="monthly">Último Mes</option>
        </select>
      </div>

      {loadingSales ? (
        <div className="chart-empty-msg" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', minHeight: '200px' }}>
          <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          <span>Cargando tendencia de ventas...</span>
        </div>
      ) : salesChartData.length > 0 ? (
        <div className="sales-trend-box__chart-wrap">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={salesChartData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={colors.border} />
              <XAxis dataKey="label" stroke={colors.muted} fontSize={11} tickLine={false} axisLine={{ stroke: colors.border }} />
              <YAxis stroke={colors.muted} fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
              <RechartsTooltip content={CustomTooltip} cursor={{ fill: colors.border, opacity: 0.3 }} />
              <Legend
                wrapperStyle={{ fontSize: '11px', color: colors.text, paddingTop: '10px' }}
                formatter={(value) => <span style={{ color: colors.text, marginRight: '14px', fontWeight: 500 }}>{value}</span>}
              />
              <Bar dataKey="Ventas" fill={colors.info} radius={[4, 4, 0, 0]} maxBarSize={45} />
              {canViewProfits && (
                <Bar dataKey="Ganancia" fill={colors.success} radius={[4, 4, 0, 0]} maxBarSize={45}>
                  {salesChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.Ganancia < -0.001 ? colors.danger : colors.success} />
                  ))}
                </Bar>
              )}
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="chart-empty-msg">
          No hay ventas registradas en {salesPeriod === 'weekly' ? 'la última semana' : 'el último mes'}.
        </p>
      )}
    </div>
  );
}
