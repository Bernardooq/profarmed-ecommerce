-- =====================================================
-- Profarmed Database Initialization Script v2
-- =====================================================

-- Eliminar tablas existentes si las hay (cuidado en producción)
DROP TABLE IF EXISTS ticket_messages CASCADE;

DROP TABLE IF EXISTS tickets CASCADE;

DROP TABLE IF EXISTS cartcache CASCADE;

DROP TABLE IF EXISTS orderitems CASCADE;

DROP TABLE IF EXISTS orders CASCADE;

DROP TABLE IF EXISTS pricelistitems CASCADE;

DROP TABLE IF EXISTS pricelists CASCADE;

DROP TABLE IF EXISTS products CASCADE;

DROP TABLE IF EXISTS categories CASCADE;

DROP TABLE IF EXISTS customerinfo CASCADE;

DROP TABLE IF EXISTS groupsellers CASCADE;

DROP TABLE IF EXISTS groupmarketingmanagers CASCADE;

DROP TABLE IF EXISTS salesgroups CASCADE;

DROP TABLE IF EXISTS customers CASCADE;

DROP TABLE IF EXISTS users CASCADE;

-- UUID generation is natively supported in PostgreSQL 13+ via gen_random_uuid()

-- =====================================================
-- EXTENSIONES NECESARIAS
-- =====================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =====================================================
-- TABLA: users (Usuarios internos: admin, marketing, seller)
-- =====================================================
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,  -- NO SERIAL - asignado manualmente o por backend
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'marketing', 'seller')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

-- Constraint: user_id debe ser positivo
CONSTRAINT check_user_id_positive CHECK (user_id > 0) );

CREATE INDEX idx_users_username ON users (username);

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

CREATE INDEX idx_customers_username ON customers (username);

CREATE INDEX idx_customers_email ON customers (email);
-- Foreign key indexing
CREATE INDEX idx_customers_agent_id ON customers (agent_id);

-- GIN indexes for full-text ILIKE searches
CREATE INDEX idx_customers_full_name_gin ON customers USING gin (full_name gin_trgm_ops);

CREATE INDEX idx_customers_username_gin ON customers USING gin (username gin_trgm_ops);

CREATE INDEX idx_customers_email_gin ON customers USING gin (email gin_trgm_ops);

-- =====================================================
-- TABLA: password_resets (Recuperación de contraseñas)
-- =====================================================
CREATE TABLE password_resets (
    reset_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL,
    allow BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
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
-- TABLA: groupmarketingmanagers (Relación N:M)
-- =====================================================
CREATE TABLE groupmarketingmanagers (
    group_marketing_id SERIAL PRIMARY KEY,
    sales_group_id INTEGER NOT NULL REFERENCES salesgroups (sales_group_id) ON DELETE CASCADE,
    marketing_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_group_marketing UNIQUE (sales_group_id, marketing_id)
);

CREATE INDEX idx_groupmarketingmanagers_group ON groupmarketingmanagers (sales_group_id);

CREATE INDEX idx_groupmarketingmanagers_marketing ON groupmarketingmanagers (marketing_id);

-- =====================================================
-- TABLA: groupsellers (Relación N:M)
-- =====================================================
CREATE TABLE groupsellers (
    group_seller_id SERIAL PRIMARY KEY,
    sales_group_id INTEGER NOT NULL REFERENCES salesgroups (sales_group_id) ON DELETE CASCADE,
    seller_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_group_seller UNIQUE (sales_group_id, seller_id)
);

CREATE INDEX idx_groupsellers_group ON groupsellers (sales_group_id);

CREATE INDEX idx_groupsellers_seller ON groupsellers (seller_id);

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
    is_active BOOLEAN DEFAULT TRUE,
    lock BOOLEAN NOT NULL DEFAULT FALSE,
    category_id INTEGER REFERENCES categories (category_id),
    updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_codebar ON products (codebar);

CREATE INDEX idx_products_is_active ON products (is_active);

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
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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

CREATE INDEX idx_pricelistitems_list ON pricelistitems (price_list_id);

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

CREATE INDEX idx_customerinfo_customer ON customerinfo (customer_id);

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
    assigned_seller_id INTEGER REFERENCES users (user_id),
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
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        assigned_at TIMESTAMP
    WITH
        TIME ZONE,
        validated_at TIMESTAMP
    WITH
        TIME ZONE
);

CREATE INDEX idx_orders_customer ON orders (customer_id);

CREATE INDEX idx_orders_seller ON orders (assigned_seller_id);

CREATE INDEX idx_orders_status ON orders (status);

CREATE INDEX idx_orders_created ON orders (created_at);

CREATE INDEX idx_orders_seller_status ON orders (assigned_seller_id, status);

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
    final_price NUMERIC(10, 2) NOT NULL
);

CREATE INDEX idx_orderitems_order ON orderitems (order_id);

CREATE INDEX idx_orderitems_product ON orderitems (product_id);

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

CREATE INDEX idx_cartcache_customer ON cartcache (customer_id);

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

CREATE INDEX idx_users_role ON users (role);

CREATE INDEX idx_users_active ON users (is_active);

-- Categories: Optimizar lookup por nombre durante product sync
CREATE INDEX idx_categories_name ON categories (name);

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
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tickets_creator ON tickets (creator_id, creator_type);

CREATE INDEX idx_tickets_assigned ON tickets (assigned_to);

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