import { useState, useEffect, useMemo } from 'react';
import { formatCurrency, getMexicoDateString } from '../../utils/formatUtils';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import BRAND from '../../config/brand';
import { faDollarSign, faChartLine, faChartPie } from '@fortawesome/free-solid-svg-icons';

import SalesTrendChart from './summary/SalesTrendChart';
import TopAnnualProducts from './summary/TopAnnualProducts';
import OrdersStatSection from './summary/OrdersStatSection';
import StaffCustomersSection from './summary/StaffCustomersSection';
import InventoryStatSection from './summary/InventoryStatSection';

export default function SummaryCards({ summary = {}, showTitles = true, isAdmin: propIsAdmin = false }) {
  const { isAdmin: authIsAdmin, can } = usePermissions();
  const isAdmin = propIsAdmin || authIsAdmin;
  const canViewTopProducts = isAdmin || can(PERMISSIONS.REPORTS_VIEW);
  const canViewProfits = isAdmin || can(PERMISSIONS.REPORTS_FINANCIAL);

  // Visibility Flags condicionadas por PBAC y presencia de datos en summary
  const visibility = useMemo(() => {
    const s = summary || {};
    const hasReportsPerm = isAdmin || can(PERMISSIONS.REPORTS_VIEW);
    const hasFinPerm = hasReportsPerm && (isAdmin || can(PERMISSIONS.REPORTS_FINANCIAL));
    const hasOrdersPerm = hasReportsPerm && (isAdmin || can('orders.view') || can('orders.group_view') || can('orders.view_all'));
    const hasUsersPerm = hasReportsPerm && (isAdmin || can('users.view'));
    const hasCustomersPerm = hasReportsPerm && (isAdmin || can('customers.view') || can('customers.view_all'));
    const hasCatalogPerm = hasReportsPerm && (isAdmin || can('catalog.view'));

    return {
      ventas: hasFinPerm && (s.total_revenue !== undefined || s.total_profit !== undefined),
      pedidos: hasOrdersPerm && (s.pending_orders !== undefined || s.delivered_orders !== undefined || s.shipped_orders !== undefined || s.cancelled_orders !== undefined || s.approved_orders !== undefined),
      personal: (hasUsersPerm || hasCustomersPerm) && (
        (hasCustomersPerm && s.total_customers !== undefined) ||
        (hasUsersPerm && ((Array.isArray(s.roles_breakdown) && s.roles_breakdown.length > 0) || s.total_users !== undefined))
      ),
      inventario: hasCatalogPerm && (s.total_products !== undefined || s.catalogCount !== undefined || s.low_stock_count !== undefined || s.lowStockCount !== undefined),
      hasUsersPerm,
      hasCustomersPerm
    };
  }, [summary, isAdmin, can]);

  // ESTADO PARA TOP PRODUCTOS ANUALES (SOLO ADMIN)
  const [topProducts, setTopProducts] = useState([]);
  const currentSystemYear = new Date().getFullYear();
  const [topYear, setTopYear] = useState(currentSystemYear);
  const [topSortBy, setTopSortBy] = useState('orders');
  const [loadingTop, setLoadingTop] = useState(false);

  // Estado para el Calendario / Picker de Año
  const [isYearPickerOpen, setIsYearPickerOpen] = useState(false);
  const [pickerDecadeStart, setPickerDecadeStart] = useState(() => Math.floor(currentSystemYear / 10) * 10);

  useEffect(() => {
    if (canViewTopProducts) {
      let isMounted = true;
      const fetchTop = async () => {
        try {
          setLoadingTop(true);
          const { adminService } = await import('../../services/adminService');
          const res = await adminService.getTopProducts(topYear, topSortBy, 5);
          if (isMounted) setTopProducts(res?.items || []);
        } catch (err) {
          console.error('Error fetching top products:', err);
        } finally {
          if (isMounted) setLoadingTop(false);
        }
      };
      fetchTop();
      return () => { isMounted = false; };
    }
  }, [canViewTopProducts, topYear, topSortBy]);

  // ESTADO PARA MINI-GRÁFICO DE VENTAS
  const [salesPeriod, setSalesPeriod] = useState('weekly');
  const [salesChartData, setSalesChartData] = useState([]);
  const [periodTotals, setPeriodTotals] = useState({ ventas: 0, ganancia: 0 });
  const [loadingSales, setLoadingSales] = useState(false);
  const [themeTick, setThemeTick] = useState(0);

  // MutationObserver para reaccionar al cambio de tema
  useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'data-theme') {
          setThemeTick(t => t + 1);
        }
      });
    });
    observer.observe(document.documentElement, { attributes: true });
    return () => observer.disconnect();
  }, []);

  // Fetch de ventas para el gráfico
  useEffect(() => {
    if (!visibility.ventas) return;

    let isMounted = true;
    const fetchMiniSales = async () => {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - (salesPeriod === 'weekly' ? 7 : 30));

      const startStr = getMexicoDateString(start);
      const endStr = getMexicoDateString(end);

      try {
        setLoadingSales(true);
        const { adminService } = await import('../../services/adminService');
        const report = await adminService.getSalesReport(startStr, endStr);

        const salesByDate = new Map();
        let totalV = 0, totalG = 0;

        if (report && report.orders) {
          report.orders.forEach(order => {
            const dateStr = order.order_date.split(' ')[0];
            if (!salesByDate.has(dateStr)) {
              const [y, m, d] = dateStr.split('-').map(Number);
              const dateObj = new Date(y, m - 1, d);
              salesByDate.set(dateStr, {
                dateStr,
                label: dateObj.toLocaleDateString('es-MX', { month: 'short', day: 'numeric' }),
                Ventas: 0,
                Ganancia: 0
              });
            }
            salesByDate.get(dateStr).Ventas += order.total_amount;
            salesByDate.get(dateStr).Ganancia += order.order_profit || 0;
            totalV += order.total_amount;
            totalG += order.order_profit || 0;
          });
        }

        const data = Array.from(salesByDate.values()).sort((a, b) => a.dateStr.localeCompare(b.dateStr));
        if (isMounted) {
          setSalesChartData(data);
          setPeriodTotals({ ventas: totalV, ganancia: totalG });
        }
      } catch (e) {
        console.error('Error fetching mini sales', e);
      } finally {
        if (isMounted) setLoadingSales(false);
      }
    };
    fetchMiniSales();
    return () => { isMounted = false; };
  }, [salesPeriod, visibility.ventas]);

  const colors = useMemo(() => {
    // eslint-disable-next-line no-unused-vars
    const _ = themeTick;
    const style = getComputedStyle(document.documentElement);
    const get = (v) => style.getPropertyValue(v).trim();
    return {
      text: get('--color-text') || '#1a1a1a',
      muted: get('--color-text-muted') || '#666',
      border: get('--color-border') || '#e5e7eb',
      surface: get('--color-surface') || '#fff',
      primary: get('--color-primary') || BRAND.themeColor,
      success: get('--color-success') || '#22c55e',
      warning: get('--color-warning') || '#eab308',
      danger: get('--color-danger') || '#ef4444',
      info: get('--color-info') || '#3b82f6',
      secondary: get('--color-secondary') || get('--color-primary') || BRAND.themeColor,
    };
  }, [themeTick]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="chart-tooltip__title">{label || payload[0].name}</p>
          {payload.map((entry, index) => (
            <p key={index} className="chart-tooltip__item" style={{ color: entry.color || entry.payload.fill || 'inherit' }}>
              {entry.name === 'Ganancia'
                ? `${entry.value < -0.001 ? 'Pérdida' : 'Ganancia'}: ${entry.value < -0.001 ? formatCurrency(entry.value) : `+${formatCurrency(entry.value)}`}`
                : (entry.name === 'Ventas' ? `Ventas: ${formatCurrency(entry.value)}` : `${entry.name}: ${entry.value}`)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // DATOS PARA GRÁFICOS
  const pedidosData = useMemo(() => [
    { name: 'Pendientes', value: summary.pending_orders || summary.pendingOrders || 0, fill: colors.warning },
    { name: 'Aprobados', value: summary.approved_orders || 0, fill: colors.success },
    { name: 'Enviados', value: summary.shipped_orders || 0, fill: colors.info },
    { name: 'Cancelados', value: summary.cancelled_orders || 0, fill: colors.danger }
  ].filter(d => d.value > 0), [summary, colors]);

  const personalData = useMemo(() => {
    const list = [];
    if (visibility.hasCustomersPerm && summary.total_customers !== undefined) {
      list.push({ name: 'Clientes', value: summary.total_customers || 0, fill: colors.info });
    }
    if (visibility.hasUsersPerm) {
      if (Array.isArray(summary.roles_breakdown) && summary.roles_breakdown.length > 0) {
        const palette = [colors.success, colors.warning, '#8b5cf6', '#ec4899', '#06b6d4', '#10b981', '#f59e0b', '#6366f1'];
        summary.roles_breakdown
          .filter(r => r.slug !== 'admin')
          .forEach((r, idx) => {
            list.push({
              name: r.name,
              value: r.count || 0,
              fill: palette[idx % palette.length]
            });
          });
      } else if (summary.total_users !== undefined) {
        list.push({ name: 'Personal Interno', value: summary.total_users || 0, fill: colors.success });
      }
    }
    return list.filter(d => d.value > 0);
  }, [summary, colors, visibility.hasCustomersPerm, visibility.hasUsersPerm]);

  const inventarioData = useMemo(() => {
    const total = summary.total_products || summary.catalogCount || 0;
    const low = summary.low_stock_count || summary.lowStockCount || 0;
    const out = summary.out_of_stock_count || summary.outOfStockCount || 0;
    const ok = Math.max(0, total - low - out);
    return [
      { name: 'Normal', value: ok, fill: colors.success },
      { name: 'Bajo Stock', value: low, fill: colors.warning },
      { name: 'Agotados', value: out, fill: colors.danger }
    ].filter(d => d.value > 0);
  }, [summary, colors]);

  return (
    <div className="stat-dashboard-wrapper">
      {/* 1. VENTAS Y FINANZAS */}
      {visibility.ventas && (
        <div className="stat-group">
          {showTitles && (
            <h3 className="stat-group__title">
              <FontAwesomeIcon icon={faChartLine} className="stat-group__icon" /> Ventas y Finanzas
            </h3>
          )}
          <section className="stat-grid stat-grid--finance mb-6">
            {summary.total_revenue !== undefined && (
              <div className="stat-card">
                <div className="stat-card__icon"><FontAwesomeIcon icon={faDollarSign} /></div>
                <div className="stat-card__content">
                  <span className="stat-card__value">{formatCurrency(summary.total_revenue)}</span>
                  <span className="stat-card__label">Ingresos Anuales</span>
                </div>
              </div>
            )}
            {canViewProfits && summary.total_profit !== undefined && (
              <div className="stat-card">
                <div className={`stat-card__icon ${summary.total_profit < -0.001 ? 'stat-card__icon--negative' : ''}`}>
                  <FontAwesomeIcon icon={faChartPie} />
                </div>
                <div className="stat-card__content">
                  <span className={`stat-card__value ${summary.total_profit < -0.001 ? 'text-danger' : 'text-success'}`}>
                    {summary.total_profit < -0.001 ? formatCurrency(summary.total_profit) : `+${formatCurrency(summary.total_profit)}`}
                  </span>
                  <span className="stat-card__label">
                    {summary.total_profit < -0.001 ? 'Pérdida Anual Estimada' : 'Ganancia Anual Estimada'}
                  </span>
                </div>
              </div>
            )}
          </section>

          {/* Gráfico Dinámico de Ventas en el Dashboard */}
          <SalesTrendChart
            salesPeriod={salesPeriod}
            setSalesPeriod={setSalesPeriod}
            salesChartData={salesChartData}
            periodTotals={periodTotals}
            canViewProfits={canViewProfits}
            loadingSales={loadingSales}
            colors={colors}
            CustomTooltip={CustomTooltip}
          />

          {/* TOP PRODUCTOS ANUALES EN O(1) */}
          {canViewTopProducts && (
            <TopAnnualProducts
              topProducts={topProducts}
              topYear={topYear}
              setTopYear={setTopYear}
              topSortBy={topSortBy}
              setTopSortBy={setTopSortBy}
              loadingTop={loadingTop}
              canViewProfits={canViewProfits}
              currentSystemYear={currentSystemYear}
              isYearPickerOpen={isYearPickerOpen}
              setIsYearPickerOpen={setIsYearPickerOpen}
              pickerDecadeStart={pickerDecadeStart}
              setPickerDecadeStart={setPickerDecadeStart}
            />
          )}
        </div>
      )}

      {/* 2. PEDIDOS */}
      {visibility.pedidos && (
        <OrdersStatSection
          summary={summary}
          showTitles={showTitles}
          pedidosData={pedidosData}
          colors={colors}
          CustomTooltip={CustomTooltip}
        />
      )}

      {/* 3. PERSONAL Y CLIENTES */}
      {visibility.personal && (
        <StaffCustomersSection
          summary={summary}
          showTitles={showTitles}
          visibility={visibility}
          personalData={personalData}
          colors={colors}
          CustomTooltip={CustomTooltip}
        />
      )}

      {/* 4. INVENTARIO */}
      {visibility.inventario && (
        <InventoryStatSection
          summary={summary}
          showTitles={showTitles}
          inventarioData={inventarioData}
          colors={colors}
          CustomTooltip={CustomTooltip}
        />
      )}
    </div>
  );
}