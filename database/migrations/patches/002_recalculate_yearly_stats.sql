-- ============================================================================
-- SCRIPT DE MIGRACIÓN: Cálculo e Inicialización de product_yearly_stats
-- Base: profarmed-ecommerce / profarmed_api (Profarmed, Profarmed, Demo)
--
-- Crea la tabla de estadísticas acumuladas anuales O(1) y realiza el backfill
-- histórico calculando ingresos, unidades vendidas, ganancias netas y número de pedidos
-- desde los pedidos existentes en estado ('approved', 'shipped', 'delivered').
-- ============================================================================

BEGIN;

-- 1. Crear tabla de estadísticas anuales por producto si no existe
CREATE TABLE IF NOT EXISTS product_yearly_stats (
    product_id VARCHAR(50) NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    orders_count INTEGER NOT NULL DEFAULT 0,
    units_sold INTEGER NOT NULL DEFAULT 0,
    total_revenue NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_profit NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, year)
);

-- Comentarios explicativos de auditoría
COMMENT ON TABLE product_yearly_stats IS 'Estadísticas anuales acumuladas por producto para responder en <1ms en dashboards de ventas sin selects masivos';
COMMENT ON COLUMN product_yearly_stats.orders_count IS 'Número de pedidos únicos que incluyeron este producto en el año';
COMMENT ON COLUMN product_yearly_stats.units_sold IS 'Cantidad total de piezas/cajas vendidas en el año';
COMMENT ON COLUMN product_yearly_stats.total_revenue IS 'Monto total facturado con IVA por este producto en el año';
COMMENT ON COLUMN product_yearly_stats.total_profit IS 'Ganancia neta acumulada en el año';

-- 2. Índices de aceleración para rankings y dashboards anuales
CREATE INDEX IF NOT EXISTS idx_product_yearly_orders ON product_yearly_stats (year, orders_count DESC);
CREATE INDEX IF NOT EXISTS idx_product_yearly_profit ON product_yearly_stats (year, total_profit DESC);
CREATE INDEX IF NOT EXISTS idx_product_yearly_units ON product_yearly_stats (year, units_sold DESC);

-- 3. Backfill histórico: calcular métricas a partir del historial real de pedidos
INSERT INTO product_yearly_stats (
    product_id, 
    year, 
    orders_count, 
    units_sold, 
    total_revenue, 
    total_profit, 
    updated_at
)
SELECT 
    oi.product_id,
    EXTRACT(YEAR FROM (o.created_at AT TIME ZONE 'America/Mexico_City'))::INTEGER AS year,
    COUNT(DISTINCT o.order_id)::INTEGER AS orders_count,
    COALESCE(SUM(oi.quantity), 0)::INTEGER AS units_sold,
    COALESCE(SUM(oi.final_price * oi.quantity), 0.00)::NUMERIC(12, 2) AS total_revenue,
    COALESCE(SUM((COALESCE(oi.price_without_iva, 0) - COALESCE(oi.base_price, 0)) * oi.quantity), 0.00)::NUMERIC(12, 2) AS total_profit,
    NOW() AS updated_at
FROM orders o
JOIN orderitems oi ON o.order_id = oi.order_id
WHERE o.status IN ('approved', 'shipped', 'delivered')
  AND oi.product_id IS NOT NULL
GROUP BY 
    oi.product_id, 
    EXTRACT(YEAR FROM (o.created_at AT TIME ZONE 'America/Mexico_City'))
ON CONFLICT (product_id, year) DO UPDATE SET
    orders_count = EXCLUDED.orders_count,
    units_sold = EXCLUDED.units_sold,
    total_revenue = EXCLUDED.total_revenue,
    total_profit = EXCLUDED.total_profit,
    updated_at = NOW();

COMMIT;
