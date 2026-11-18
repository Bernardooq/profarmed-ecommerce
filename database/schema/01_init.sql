-- =====================================================
-- Profarmed Database Initialization Script v2
-- =====================================================

DROP TABLE IF EXISTS order_stock_holds CASCADE;

DROP TABLE IF EXISTS system_configs CASCADE;

DROP TABLE IF EXISTS product_yearly_stats CASCADE;

DROP TABLE IF EXISTS product_discounts CASCADE;

DROP TABLE IF EXISTS promo_ad_items CASCADE;

DROP TABLE IF EXISTS promo_ad_sections CASCADE;

DROP TABLE IF EXISTS announcements CASCADE;

DROP TABLE IF EXISTS order_stats CASCADE;

DROP TABLE IF EXISTS client_requests CASCADE;

DROP TABLE IF EXISTS contact_messages CASCADE;

DROP TABLE IF EXISTS favoritelistitems CASCADE;

DROP TABLE IF EXISTS favoritelists CASCADE;

DROP TABLE IF EXISTS ticket_messages CASCADE;

DROP TABLE IF EXISTS tickets CASCADE;

DROP TABLE IF EXISTS cartcache CASCADE;

DROP TABLE IF EXISTS product_recommendations CASCADE;

DROP TABLE IF EXISTS warehouse_items CASCADE;

DROP TABLE IF EXISTS warehouse_containers CASCADE;

DROP TABLE IF EXISTS orderitems CASCADE;

DROP TABLE IF EXISTS warehouse_splits CASCADE;

DROP TABLE IF EXISTS orders CASCADE;

DROP TABLE IF EXISTS pricelistitems CASCADE;

DROP TABLE IF EXISTS pricelists CASCADE;

DROP TABLE IF EXISTS products CASCADE;

DROP TABLE IF EXISTS categories CASCADE;

DROP TABLE IF EXISTS customerinfo CASCADE;

DROP TABLE IF EXISTS group_users CASCADE;

DROP TABLE IF EXISTS salesgroups CASCADE;

DROP TABLE IF EXISTS customers CASCADE;

DROP TABLE IF EXISTS users CASCADE;

-- UUID generation is natively supported in PostgreSQL 13+ via gen_random_uuid()

-- =====================================================
-- EXTENSIONES NECESARIAS
-- =====================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =====================================================
-- TABLA: roles (Roles dinámicos del sistema para usuarios internos)
-- =====================================================
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_roles_slug ON roles (slug);

-- =====================================================
-- TABLA: permissions (Catálogo maestro PBAC de permisos del sistema)
-- =====================================================
CREATE TABLE permissions (
    permission_code VARCHAR(100) PRIMARY KEY,
    module VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    depends_on VARCHAR(100) REFERENCES permissions (permission_code) ON DELETE SET NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permissions_module ON permissions (module);

-- =====================================================
-- TABLA: role_permissions (Matriz N:M de permisos por rol)
-- =====================================================
CREATE TABLE role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles (role_id) ON DELETE CASCADE,
    permission_code VARCHAR(100) NOT NULL REFERENCES permissions (permission_code) ON DELETE CASCADE,
    granted_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (role_id, permission_code)
);

CREATE INDEX idx_role_permissions_role ON role_permissions (role_id);

CREATE INDEX idx_role_permissions_perm ON role_permissions (permission_code);

-- =====================================================
-- TABLA: users (Usuarios internos con rol asignado por FK)
-- =====================================================
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,  -- NO SERIAL - asignado manualmente o por backend
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT TRUE,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    locked_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

-- Constraint: user_id debe ser positivo
CONSTRAINT check_user_id_positive CHECK (user_id > 0) );

CREATE INDEX idx_users_role_id ON users (role_id);

CREATE INDEX idx_users_email ON users (email);

-- GIN indexes for full-text ILIKE searches
CREATE INDEX idx_users_full_name_gin ON users USING gin (full_name gin_trgm_ops);

CREATE INDEX idx_users_username_gin ON users USING gin (username gin_trgm_ops);

CREATE INDEX idx_users_email_gin ON users USING gin (email gin_trgm_ops);

-- =====================================================
-- TABLA: customers (Clientes del e-commerce)
-- =====================================================
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255), -- Email NO es unico - varios clientes pueden compartir email
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    locked_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        agent_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
        notificate BOOLEAN NOT NULL DEFAULT FALSE,
        CONSTRAINT customers_username_unique UNIQUE (username)
);

CREATE INDEX idx_users_is_locked ON users (is_locked);
CREATE INDEX idx_customers_is_locked ON customers (is_locked);

-- idx_customers_username omitido: username ya tiene índice B-Tree único por customers_username_unique
CREATE INDEX idx_customers_email ON customers (email);
-- Foreign key indexing
CREATE INDEX idx_customers_agent_id ON customers (agent_id);

-- GIN indexes for full-text ILIKE searches
CREATE INDEX idx_customers_full_name_gin ON customers USING gin (full_name gin_trgm_ops);

CREATE INDEX idx_customers_username_gin ON customers USING gin (username gin_trgm_ops);

CREATE INDEX idx_customers_email_gin ON customers USING gin (email gin_trgm_ops);

-- =====================================================
-- TABLA: password_resets (Recuperación de contraseñas para clientes y usuarios)
-- =====================================================
CREATE TABLE password_resets (
    reset_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers (customer_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users (user_id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50),
    allow BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
        expires_at TIMESTAMP
    WITH
        TIME ZONE NOT NULL,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_password_resets_customer_id ON password_resets (customer_id);

CREATE INDEX idx_password_resets_user_id ON password_resets (user_id);

CREATE INDEX idx_password_resets_code ON password_resets (code);

-- =====================================================
-- TABLA: salesgroups (Grupos de ventas)
-- =====================================================
CREATE TABLE salesgroups (
    sales_group_id SERIAL PRIMARY KEY,
    group_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- GIN indexes for full-text ILIKE searches
CREATE INDEX idx_salesgroups_group_name_gin ON salesgroups USING gin (group_name gin_trgm_ops);

-- =====================================================
-- TABLA: group_users (Relación N:M Usuarios internos con Grupos de Venta)
-- Unifica y reemplaza las antiguas tablas groupsellers y groupmarketingmanagers
-- =====================================================
CREATE TABLE group_users (
    sales_group_id INTEGER NOT NULL REFERENCES salesgroups (sales_group_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (sales_group_id, user_id)
);

CREATE INDEX idx_group_users_user ON group_users (user_id);

-- =====================================================
-- TABLA: categories (Categorías de productos)
-- =====================================================
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- GIN indexes for full-text ILIKE searches
CREATE INDEX idx_categories_name_gin ON categories USING gin (name gin_trgm_ops);

CREATE INDEX idx_categories_description_gin ON categories USING gin (description gin_trgm_ops);

-- =====================================================
-- TABLA: products (Productos del catálogo)
-- =====================================================
CREATE TABLE products (
    product_id VARCHAR(50) PRIMARY KEY,
    codebar VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    descripcion_2 TEXT,
    unidad_medida VARCHAR(10),
    base_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    iva_percentage NUMERIC(5, 2) DEFAULT 0.00,
    image_url VARCHAR(255),
    image_version INTEGER DEFAULT 1,
    stock_count INTEGER DEFAULT 0,
    location VARCHAR(100) NOT NULL DEFAULT '',
    display_priority INTEGER NOT NULL DEFAULT 1000000,
    is_active BOOLEAN DEFAULT TRUE,
    lock BOOLEAN NOT NULL DEFAULT FALSE,
    category_id INTEGER REFERENCES categories (category_id),
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_codebar ON products (codebar);

CREATE INDEX idx_products_is_active ON products (is_active);

CREATE INDEX idx_products_display_priority ON products (display_priority ASC, product_id DESC);

CREATE INDEX idx_products_created_at ON products (created_at DESC);

CREATE INDEX idx_products_lock ON products (lock);

CREATE INDEX idx_products_category ON products (category_id);

-- GIN indexes for full-text ILIKE searches
CREATE INDEX idx_products_product_id_gin ON products USING gin (product_id gin_trgm_ops);

CREATE INDEX idx_products_codebar_gin ON products USING gin (codebar gin_trgm_ops);

CREATE INDEX idx_products_name_gin ON products USING gin (name gin_trgm_ops);

CREATE INDEX idx_products_description_gin ON products USING gin (description gin_trgm_ops);

CREATE INDEX idx_products_descripcion_2_gin ON products USING gin (descripcion_2 gin_trgm_ops);

-- =====================================================
-- TABLA: pricelists (Listas de precios)
-- =====================================================
CREATE TABLE pricelists (
    price_list_id INTEGER PRIMARY KEY,
    list_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_public_internal BOOLEAN NOT NULL DEFAULT FALSE,
    is_public_storefront BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pricelists_public_internal ON pricelists (is_public_internal, is_active);
CREATE INDEX idx_pricelists_public_storefront ON pricelists (is_public_storefront, is_active);


-- =====================================================
-- TABLA: pricelistitems (Markup por producto en lista)
-- =====================================================
CREATE TABLE pricelistitems (
    price_list_id INTEGER NOT NULL REFERENCES pricelists (price_list_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    markup_percentage NUMERIC(5, 2) NOT NULL,
    final_price NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (price_list_id, product_id)
);

-- idx_pricelistitems_list omitido: price_list_id es la columna inicial del PRIMARY KEY (price_list_id, product_id)
CREATE INDEX idx_pricelistitems_product ON pricelistitems (product_id);

-- NOTA: Se eliminó idx_pricelistitems_composite ya que el CONSTRAINT unique_pricelist_product crea un índice B-Tree idéntico implícitamente.

-- =====================================================
-- TABLA: customerinfo (Información comercial de clientes)
-- =====================================================
CREATE TABLE customerinfo (
    customer_info_id SERIAL PRIMARY KEY,
    customer_id INTEGER UNIQUE NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    business_name VARCHAR(255) NOT NULL,
    rfc VARCHAR(13),
    sales_group_id INTEGER REFERENCES salesgroups (sales_group_id),
    price_list_id INTEGER REFERENCES pricelists (price_list_id),
    address_1 TEXT,
    address_2 TEXT,
    address_3 TEXT,
    telefono_1 VARCHAR(15),
    telefono_2 VARCHAR(15)
);

CREATE INDEX idx_customerinfo_rfc ON customerinfo (rfc);

-- idx_customerinfo_customer omitido: customer_id ya tiene índice único por su constraint UNIQUE

CREATE INDEX idx_customerinfo_group ON customerinfo (sales_group_id);

CREATE INDEX idx_customerinfo_pricelist ON customerinfo (price_list_id);

-- GIN index para busquedas ILIKE en crud_sales_group.py
CREATE INDEX idx_customerinfo_rfc_gin ON customerinfo USING gin (rfc gin_trgm_ops);

-- =====================================================
-- TABLA: orders (Pedidos)
-- =====================================================
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
    assigned_user_id INTEGER REFERENCES users (user_id),
    assigned_by_user_id INTEGER REFERENCES users (user_id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending_validation' CHECK (
        status IN (
            'pending_validation',
            'approved',
            'shipped',
            'delivered',
            'cancelled'
        )
    ),
    total_amount NUMERIC(12, 2) DEFAULT 0.00,
    order_profit NUMERIC(12, 2) DEFAULT 0.00,
    shipping_cost NUMERIC(10, 2) DEFAULT 0.00,
    shipping_address_number INTEGER CHECK (
        shipping_address_number BETWEEN 1 AND 3
    ),
    shipping_address_snapshot TEXT,
    assignment_notes TEXT,
    order_notes TEXT,
    invoice_type VARCHAR(50) NOT NULL DEFAULT 'factura',
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        assigned_at TIMESTAMP
    WITH
        TIME ZONE,
        validated_at TIMESTAMP
    WITH
        TIME ZONE,
        sent_to_warehouse BOOLEAN NOT NULL DEFAULT FALSE,
        warehouse_status VARCHAR(30) DEFAULT NULL,
        audit_verdict VARCHAR(50) NOT NULL DEFAULT 'clean',
        total_splits INTEGER DEFAULT 1,
        warehouse_sent_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
        warehouse_sent_at TIMESTAMP
    WITH
        TIME ZONE,
        warehouse_show_details BOOLEAN NOT NULL DEFAULT FALSE,
        is_synced BOOLEAN NOT NULL DEFAULT FALSE
);

-- idx_orders_is_synced optimiza consultas de filtrado por sincronización ERP
CREATE INDEX idx_orders_is_synced ON orders (is_synced);

CREATE INDEX idx_orders_customer ON orders (customer_id, created_at DESC);

-- idx_orders_status_created cubre búsquedas por status y resuelve paginación ORDER BY created_at DESC sin sort en RAM
CREATE INDEX idx_orders_status_created ON orders (status, created_at DESC);

-- idx_orders_created resuelve ordenamiento global ORDER BY created_at DESC y filtros por rango de fechas
CREATE INDEX idx_orders_created ON orders (created_at DESC);

-- idx_orders_user_status cubre tanto WHERE assigned_user_id = X como WHERE assigned_user_id = X AND status = Y
CREATE INDEX idx_orders_user_status ON orders (assigned_user_id, status);

-- idx_orders_warehouse_verdict cubre filtros por veredicto pericial de auditoría en pedidos de almacén
CREATE INDEX idx_orders_warehouse_verdict ON orders (audit_verdict)
WHERE
    sent_to_warehouse = TRUE;

-- Índice bidireccional optimizado para cola FIFO e historial (Forward Scan para ASC, Backward Scan para DESC sin sort en RAM)
CREATE INDEX idx_orders_warehouse_fifo ON orders (
    warehouse_sent_at ASC,
    order_id ASC
)
WHERE
    sent_to_warehouse = TRUE;

-- Índice compuesto bidireccional para paginación y ordenamiento con filtro de estatus en t4g.micro (Zero Sort Memory)
CREATE INDEX idx_orders_wh_status_fifo ON orders (
    warehouse_status,
    warehouse_sent_at ASC,
    order_id ASC
)
WHERE
    sent_to_warehouse = TRUE;

-- =====================================================
-- TABLA: warehouse_containers (Canastas Físicas con QR / Totes)
-- =====================================================
CREATE TABLE warehouse_containers (
    container_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    qr_code VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available' CHECK (
        status IN (
            'available',
            'in_use',
            'damaged',
            'maintenance',
            'retired',
            'unavailable'
        )
    ),
    current_split_id UUID DEFAULT NULL,
    current_user_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_containers_qr ON warehouse_containers (qr_code);

CREATE INDEX idx_containers_status ON warehouse_containers (status);

CREATE INDEX idx_containers_split ON warehouse_containers (current_split_id);

-- =====================================================
-- TABLA: warehouse_splits (Lotes de Surtido Lógico / Físico)
-- =====================================================
CREATE TABLE warehouse_splits (
    split_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    order_id BIGINT NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    split_number INTEGER NOT NULL,
    total_splits INTEGER NOT NULL,
    split_code VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'picking',
            'in_progress',
            'ready_for_check',
            'checking',
            'completed',
            'cancelled'
        )
    ),
    picker_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    checker_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    security_seal_folio VARCHAR(50),
    started_at TIMESTAMP
    WITH
        TIME ZONE,
        picking_completed_at TIMESTAMP
    WITH
        TIME ZONE,
        checking_started_at TIMESTAMP
    WITH
        TIME ZONE,
        completed_at TIMESTAMP
    WITH
        TIME ZONE,
        admin_override_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
        admin_override_at TIMESTAMP
    WITH
        TIME ZONE,
        active_container_id UUID REFERENCES warehouse_containers (container_id) ON DELETE SET NULL,
        uses_containers BOOLEAN NOT NULL DEFAULT FALSE,
        CONSTRAINT uq_order_split UNIQUE (order_id, split_number)
);

ALTER TABLE warehouse_containers
ADD CONSTRAINT fk_containers_current_split FOREIGN KEY (current_split_id) REFERENCES warehouse_splits (split_id) ON DELETE SET NULL;

CREATE INDEX idx_splits_order_status ON warehouse_splits (order_id, status);

CREATE INDEX idx_splits_code ON warehouse_splits (split_code);

CREATE INDEX idx_splits_picker ON warehouse_splits (picker_id, status);

CREATE INDEX idx_splits_checker ON warehouse_splits (checker_id, status);

CREATE INDEX idx_splits_status ON warehouse_splits (status);

CREATE INDEX idx_splits_active_container ON warehouse_splits (active_container_id);

CREATE INDEX idx_splits_seal ON warehouse_splits (security_seal_folio)
WHERE
    security_seal_folio IS NOT NULL;

-- =====================================================
-- TABLA: orderitems (Items de pedidos)
-- =====================================================
CREATE TABLE orderitems (
    order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    order_id BIGINT NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    base_price NUMERIC(10, 2) NOT NULL,
    markup_percentage NUMERIC(5, 2) NOT NULL,
    iva_percentage NUMERIC(5, 2) NOT NULL,
    price_without_iva NUMERIC(10, 2) NOT NULL,
    final_price NUMERIC(10, 2) NOT NULL,
    discount_applied NUMERIC(5, 2) DEFAULT 0.00,
    discount_type VARCHAR(20) DEFAULT 'none'
);

CREATE INDEX idx_orderitems_order ON orderitems (order_id);

CREATE INDEX idx_orderitems_product ON orderitems (product_id);

-- =====================================================
-- TABLA: warehouse_items (Partidas Granulares de Almacén)
-- =====================================================


CREATE TABLE warehouse_items (
    warehouse_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    split_id UUID NOT NULL REFERENCES warehouse_splits (split_id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES orderitems (order_item_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id),
    container_id UUID REFERENCES warehouse_containers (container_id) ON DELETE SET NULL,
    
    required_quantity INTEGER NOT NULL CHECK (required_quantity > 0),

-- 1er Filtro: Surtido en Piso (Picker)
picked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_scanned_qty >= 0),
picked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (picked_boxes >= 0),
picked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (picked_box_prods >= 0),
picked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_manual_qty >= 0),
picked_manual_reason VARCHAR(255) DEFAULT NULL,
picked_total_qty INTEGER GENERATED ALWAYS AS (
    picked_scanned_qty + picked_box_prods + picked_manual_qty
) STORED,
picked_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
picked_at TIMESTAMP
WITH
    TIME ZONE,

-- 2do Filtro: Mesa de Control y Revisión (Checker)
checked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_scanned_qty >= 0),
checked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (checked_boxes >= 0),
checked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (checked_box_prods >= 0),
checked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_manual_qty >= 0),
checked_manual_reason VARCHAR(255) DEFAULT NULL,
checked_total_qty INTEGER GENERATED ALWAYS AS (
    checked_scanned_qty + checked_box_prods + checked_manual_qty
) STORED,
checked_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
checked_at TIMESTAMP
WITH
    TIME ZONE,

-- Estatus y Auditoría
status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'partial', 'completed', 'discrepancy')
    ),
    admin_override_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    admin_override_at TIMESTAMP WITH TIME ZONE,
    admin_override_note TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wh_items_split ON warehouse_items (split_id);

CREATE INDEX idx_wh_items_order_item ON warehouse_items (order_item_id);

CREATE INDEX idx_wh_items_product ON warehouse_items (product_id);

CREATE INDEX idx_wh_items_container ON warehouse_items (container_id);

CREATE INDEX idx_wh_items_status ON warehouse_items (status);

-- =====================================================
-- TABLA: warehouse_container_items (Distribución Consolidada por Canasta Física)
-- =====================================================
CREATE TABLE warehouse_container_items (
    container_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    split_id UUID NOT NULL REFERENCES warehouse_splits (split_id) ON DELETE CASCADE,
    container_id UUID NOT NULL REFERENCES warehouse_containers (container_id) ON DELETE CASCADE,
    warehouse_item_id UUID REFERENCES warehouse_items (warehouse_item_id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES orderitems (order_item_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id),

-- 1er Filtro: Surtido en Piso (Picker) en esta canasta
picked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_scanned_qty >= 0),
picked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (picked_boxes >= 0),
picked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (picked_box_prods >= 0),
picked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_manual_qty >= 0),
picked_total_qty INTEGER GENERATED ALWAYS AS (
    picked_scanned_qty + picked_box_prods + picked_manual_qty
) STORED,

-- 2do Filtro: Mesa de Control y Revisión (Checker) en esta canasta

checked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_scanned_qty >= 0),
    checked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (checked_boxes >= 0),
    checked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (checked_box_prods >= 0),
    checked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_manual_qty >= 0),
    checked_total_qty INTEGER GENERATED ALWAYS AS (
        checked_scanned_qty + checked_box_prods + checked_manual_qty
    ) STORED,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_split_container_product UNIQUE (split_id, container_id, product_id)
);

CREATE INDEX idx_wh_ci_split ON warehouse_container_items (split_id);

CREATE INDEX idx_wh_ci_container ON warehouse_container_items (container_id);

CREATE INDEX idx_wh_ci_item ON warehouse_container_items (warehouse_item_id);

CREATE INDEX idx_wh_ci_product ON warehouse_container_items (product_id);

CREATE INDEX idx_wh_ci_order_item ON warehouse_container_items (order_item_id);

-- =====================================================
-- TABLA: cartcache (Carrito de compras temporal)
-- =====================================================
CREATE TABLE cartcache (
    cart_cache_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_cart_item UNIQUE (customer_id, product_id)
);

-- idx_cartcache_customer omitido: customer_id es la columna inicial del constraint unique_cart_item
CREATE INDEX idx_cartcache_product ON cartcache (product_id);

-- =====================================================
-- TABLA: product_recommendations (Recomendacion de )
-- =====================================================
CREATE TABLE product_recommendations (
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    recommended_product_id VARCHAR(50) NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    recommendation_type VARCHAR(50) DEFAULT 'intersection/union',
    score NUMERIC(3, 2) DEFAULT 1.0,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (
            product_id,
            recommended_product_id
        ),
        CONSTRAINT check_not_self_recommended CHECK (
            product_id <> recommended_product_id
        )
);

CREATE INDEX idx_prod_rec_source ON product_recommendations (product_id);

CREATE INDEX idx_prod_rec_recommended ON product_recommendations (recommended_product_id);

-- =====================================================
-- ADDITIONAL INDEXES FOR UPSERT & SYNC OPTIMIZATION
-- =====================================================
-- Indexes added to support performance during ERP synchronizations
-- and cleanup operations based on updated_at timestamps.

-- Product Sync Optimization
CREATE INDEX idx_products_updated_at ON products (updated_at);

-- PriceListItems Massive UPSERT Optimization
CREATE INDEX idx_pricelistitems_updated_at ON pricelistitems (updated_at);

-- Customer Sync Optimization
CREATE INDEX idx_customers_updated_at ON customers (updated_at);

CREATE INDEX idx_customers_active ON customers (is_active);

-- Users: Optimizar sincronización de vendedores
CREATE INDEX idx_users_updated_at ON users (updated_at);

CREATE INDEX IF NOT EXISTS idx_users_role_id ON users (role_id);

CREATE INDEX idx_users_active ON users (is_active);

-- Categories: lookup por nombre ya cubierto por el índice único del constraint UNIQUE (name)
CREATE INDEX idx_categories_updated_at ON categories (updated_at);

-- PriceLists: Optimizar cleanup de listas no sincronizadas
CREATE INDEX idx_pricelists_updated_at ON pricelists (updated_at);

-- =====================================================
-- TABLA: tickets (Sistema de Soporte)
-- =====================================================
CREATE TABLE tickets (
    ticket_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'open' CHECK (
        status IN (
            'open',
            'in_progress',
            'resolved',
            'cancelled',
            'escalated'
        )
    ),
    priority VARCHAR(50) NOT NULL DEFAULT 'medium' CHECK (
        priority IN (
            'low',
            'medium',
            'high',
            'urgent'
        )
    ),
    creator_id INTEGER NOT NULL,
    creator_type VARCHAR(50) NOT NULL CHECK (
        creator_type IN ('customer', 'user')
    ),
    assigned_to INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    order_id BIGINT REFERENCES orders (order_id) ON DELETE SET NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tickets_creator ON tickets (creator_id, creator_type);

CREATE INDEX idx_tickets_assigned ON tickets (assigned_to);

CREATE INDEX idx_tickets_order ON tickets (order_id);

CREATE INDEX idx_tickets_status ON tickets (status);

CREATE INDEX idx_tickets_created_at ON tickets (created_at DESC);

-- =====================================================
-- TABLA: ticket_messages (Hilos de Soporte)
-- =====================================================
CREATE TABLE ticket_messages (
    message_id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL,
    sender_type VARCHAR(50) NOT NULL CHECK (
        sender_type IN ('customer', 'user')
    ),
    content TEXT NOT NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ticket_messages_ticket ON ticket_messages (ticket_id);

CREATE INDEX idx_ticket_messages_created_at ON ticket_messages (created_at ASC);

-- =====================================================
-- TABLA: favoritelists (Listas de compras preestablecidas)
-- =====================================================
CREATE TABLE favoritelists (
    list_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    customer_id INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_list_name_per_customer UNIQUE (customer_id, name)
);

CREATE INDEX idx_favoritelists_customer ON favoritelists (customer_id);

-- GIN index for partial/case-insensitive searches (ILIKE)
CREATE INDEX idx_favoritelists_name_gin ON favoritelists USING gin (name gin_trgm_ops);

-- =====================================================
-- TABLA: favoritelistitems (Productos en las listas)
-- =====================================================
CREATE TABLE favoritelistitems (
    list_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    list_id UUID NOT NULL REFERENCES favoritelists (list_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_product_per_list UNIQUE (list_id, product_id)
);

CREATE INDEX idx_favoritelistitems_list ON favoritelistitems (list_id);

-- =====================================================
-- TABLA: contact_messages (Mensajes de Contacto)
-- =====================================================
CREATE TABLE contact_messages (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    message VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (
        status IN ('pending', 'contacted')
    ),
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contact_messages_status ON contact_messages (status);

CREATE INDEX idx_contact_messages_created ON contact_messages (created_at DESC);

-- GIN indexes for full-text ILIKE searches (name, email, subject)
CREATE INDEX idx_contact_messages_full_name_gin ON contact_messages USING gin (full_name gin_trgm_ops);

CREATE INDEX idx_contact_messages_email_gin ON contact_messages USING gin (email gin_trgm_ops);

CREATE INDEX idx_contact_messages_subject_gin ON contact_messages USING gin (subject gin_trgm_ops);

-- =====================================================
-- TABLA: client_requests (Solicitudes de clientes)
-- =====================================================
CREATE TABLE client_requests (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    message VARCHAR(500) NOT NULL,
    id_pdf_key VARCHAR(500) NOT NULL,
    sanitary_license_pdf_key VARCHAR(500) NOT NULL,
    proof_of_address_pdf_key VARCHAR(500) NOT NULL,
    tax_cert_pdf_key VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'approved',
            'rejected'
        )
    ),
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_client_requests_status ON client_requests (status);

CREATE INDEX idx_client_requests_created ON client_requests (created_at DESC);

-- GIN indexes for full-text ILIKE searches (name, email, subject)
CREATE INDEX idx_client_requests_full_name_gin ON client_requests USING gin (full_name gin_trgm_ops);

CREATE INDEX idx_client_requests_email_gin ON client_requests USING gin (email gin_trgm_ops);

CREATE INDEX idx_client_requests_subject_gin ON client_requests USING gin (subject gin_trgm_ops);

-- =====================================================
-- TABLA: order_stats (Conteos desnormalizados de pedidos)
-- Mantenida desde Python (crud_order_stats).
-- La asociación grupo se determina por customer_id → customerinfo.sales_group_id
-- sales_group_id = 0 → conteo global para admin
-- sales_group_id > 0 → conteo por grupo de ventas
-- =====================================================
CREATE TABLE IF NOT EXISTS order_stats (
    sales_group_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (sales_group_id, status)
);

-- =====================================================
-- MAINTENANCE & AUTOVACUUM TUNING
-- =====================================================
-- Optimize autovacuum settings for tables with high mutation rates (UPDATE/DELETE).
-- Reducing the scale factor to 5% prevents Dead Tuple accumulation,
-- ensuring optimal disk usage and query latency.
ALTER TABLE orders SET( autovacuum_vacuum_scale_factor = 0.05 );

ALTER TABLE cartcache SET( autovacuum_vacuum_scale_factor = 0.05 );

CREATE TABLE IF NOT EXISTS announcements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    content TEXT NOT NULL,
    img VARCHAR(255),
    img_version INTEGER DEFAULT 1,
    type VARCHAR(20) NOT NULL CHECK (
        type IN ('story', 'popup', 'footer')
    ),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (
        status IN ('activo', 'inactivo')
    ),
    start_date TIMESTAMP
    WITH
        TIME ZONE NOT NULL,
        end_date TIMESTAMP
    WITH
        TIME ZONE,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_send TIMESTAMP
    WITH
        TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_announcements_active_lookup ON announcements (type, status, start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_announcements_expiry ON announcements (status, end_date);

CREATE INDEX IF NOT EXISTS idx_announcements_created ON announcements (created_at DESC);

-- =====================================================
-- TABLAS: promo_ad_sections & promo_ad_items (Publicidad de Inicio)
-- =====================================================
CREATE TABLE IF NOT EXISTS promo_ad_sections (
    section_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    title VARCHAR(150),
    layout_type INTEGER NOT NULL CHECK (layout_type IN (1, 2, 3, 4)),
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_promo_ad_sections_active_order ON promo_ad_sections (is_active, display_order);

CREATE TABLE IF NOT EXISTS promo_ad_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    section_id UUID NOT NULL REFERENCES promo_ad_sections (section_id) ON DELETE CASCADE,
    slot INTEGER NOT NULL DEFAULT 1 CHECK (slot BETWEEN 1 AND 4),
    display_order INTEGER NOT NULL DEFAULT 0,
    title VARCHAR(150),
    link_url VARCHAR(500),
    img_desktop VARCHAR(255) NOT NULL,
    img_tablet VARCHAR(255),
    img_mobile VARCHAR(255),
    img_version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_promo_ad_items_section_slot ON promo_ad_items (section_id, slot, display_order);
CREATE INDEX IF NOT EXISTS idx_promo_ad_items_active ON promo_ad_items (is_active);

-- =====================================================
-- TABLA: product_discounts (Descuentos en productos)
-- =====================================================
CREATE TABLE IF NOT EXISTS product_discounts (
    discount_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    price_list_id INTEGER REFERENCES pricelists (price_list_id) ON DELETE CASCADE,
    discount_percentage NUMERIC(5, 2) NOT NULL CHECK (
        discount_percentage > 0
        AND discount_percentage <= 100
    ),
    start_date TIMESTAMP
    WITH
        TIME ZONE NOT NULL,
        end_date TIMESTAMP
    WITH
        TIME ZONE NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        description VARCHAR(255),
        created_by_user_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT NOW(),
        CONSTRAINT chk_discount_dates CHECK (start_date < end_date)
);

CREATE INDEX IF NOT EXISTS idx_product_discounts_lookup ON product_discounts (
    product_id,
    price_list_id,
    is_active,
    start_date,
    end_date
);

CREATE INDEX IF NOT EXISTS idx_product_discounts_active_dates ON product_discounts (
    is_active,
    start_date,
    end_date
);

CREATE INDEX IF NOT EXISTS idx_product_discounts_created ON product_discounts (created_at DESC);

-- ============================================================================
-- 4. TABLA DE ESTADÍSTICAS ANUALES POR PRODUCTO (O(1) DASHBOARD)
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_yearly_stats (
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    orders_count INTEGER NOT NULL DEFAULT 0,
    units_sold INTEGER NOT NULL DEFAULT 0,
    total_revenue NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_profit NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (product_id, year)
);

COMMENT ON
TABLE product_yearly_stats IS 'Estadísticas anuales acumuladas por producto para responder en <1ms en dashboards de ventas sin selects masivos';

COMMENT ON COLUMN product_yearly_stats.orders_count IS 'Número de pedidos únicos que incluyeron este producto en el año';

COMMENT ON COLUMN product_yearly_stats.units_sold IS 'Cantidad total de piezas/cajas vendidas en el año';

COMMENT ON COLUMN product_yearly_stats.total_revenue IS 'Monto total facturado con IVA por este producto en el año';

COMMENT ON COLUMN product_yearly_stats.total_profit IS 'Ganancia neta acumulada en el año';

CREATE INDEX IF NOT EXISTS idx_product_yearly_orders ON product_yearly_stats (year, orders_count DESC);

CREATE INDEX IF NOT EXISTS idx_product_yearly_profit ON product_yearly_stats (year, total_profit DESC);

CREATE INDEX IF NOT EXISTS idx_product_yearly_units ON product_yearly_stats (year, units_sold DESC);

-- ============================================================================
-- 5. TABLA DE CONFIGURACIONES DEL SISTEMA (system_configs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_configs (
    config_id INTEGER PRIMARY KEY,
    config_name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON
TABLE system_configs IS 'Configuraciones persistentes y globales del sistema (flags operacionales)';

INSERT INTO system_configs (config_id, config_name, description, is_active)
VALUES 
    (101, 'order.apartar', 'Aparta provisionalmente el stock de los productos al crear pedidos web hasta que se aprueben o sincronicen con el ERP SAI.', FALSE),
    (102, 'order.discount', 'Descuenta inmediatamente las existencias del catálogo web en cuanto se crea un pedido antes del proceso en almacén/SAI.', FALSE),
    (103, 'catalog.order_by_priority', 'Prioriza en el catálogo y filtros por defecto los productos con display_priority manual (1 a 999,999) y después los generales.', TRUE),
    (104, 'catalog.weekly_rotation', 'Habilita la rotación y barajado periódico de productos sin prioridad personalizada (>= 1,000,000) para dar variedad visual al cliente.', FALSE),
    (105, 'user.auto_create_sales_group', 'Crea automáticamente un grupo de ventas vinculado al registrar o sincronizar un nuevo colaborador/usuario interno.', TRUE),
    (106, 'customer.auto_assign_agent_group', 'Asigna automáticamente al cliente al grupo comercial de su agente/vendedor asignado al crear, actualizar o sincronizar.', TRUE),
    (
        107,
        'pricing.tax_inclusive',
        'Indica que los precios de listas ya incluyen IVA (modelo neto mostrador/farmacia). Al estar activo, no suma IVA adicional en catálogo ni checkout y desglosa el impuesto hacia abajo.',
        FALSE
    )
ON CONFLICT (config_id) DO UPDATE SET
    config_name = EXCLUDED.config_name,
    description = EXCLUDED.description,
    updated_at = NOW();

-- ============================================================================
-- 6. TABLA DE APARTADOS TEMPORALES DE STOCK POR PEDIDO (order_stock_holds)
-- ============================================================================
CREATE TABLE IF NOT EXISTS order_stock_holds (
    order_id BIGINT NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (order_id, product_id)
);

COMMENT ON
TABLE order_stock_holds IS 'Unidades apartadas provisionalmente por pedido para descontar del stock mientras se autoriza o sincroniza el ERP';

CREATE INDEX IF NOT EXISTS idx_order_stock_holds_product ON order_stock_holds (product_id);

CREATE INDEX IF NOT EXISTS idx_order_stock_holds_order ON order_stock_holds (order_id);
