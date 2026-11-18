-- ============================================================================
-- SCRIPT DE MIGRACIÓN CONSOLIDADO, ROBUSTO Y ADAPTATIVO
-- Origen: legacy_db_init.sql (Esquema Legacy)
-- Destino: db_init.sql (Esquema Canónico Actual)
-- Base: profarmed-ecommerce / profarmed_api (Profarmed, Profarmed, Demo)
--
-- CARACTERÍSTICAS PRINCIPALES:
-- 1. Idempotente: seguro para re-ejecución sin pérdida de datos.
-- 2. Adaptativo: migra datos existentes (vendedores, gerentes, roles, pedidos,
--    estadísticas, etc.) antes de retirar esquemas obsoletos.
-- 3. Fidelidad 100%: cubre todas las tablas, columnas, restricciones e índices
--    que existen en db_init.sql y no estaban en legacy_db_init.sql.
-- 4. Estructura pura: excluye el sembrado de permisos PBAC y de configs
--    (delegados a seed_roles_permissions.sql y seed_system_configs.sql).
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. EXTENSIONES REQUERIDAS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- 2. TABLAS BASE DE CONTROL DE ACCESO PBAC (roles, permissions, role_permissions)
--    Requeridas para la migración de users.role -> users.role_id
-- ============================================================================
CREATE TABLE IF NOT EXISTS roles (
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

CREATE TABLE IF NOT EXISTS permissions (
    permission_code VARCHAR(100) PRIMARY KEY,
    module VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    depends_on VARCHAR(100) REFERENCES permissions (permission_code) ON DELETE SET NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles (role_id) ON DELETE CASCADE,
    permission_code VARCHAR(100) NOT NULL REFERENCES permissions (permission_code) ON DELETE CASCADE,
    granted_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (role_id, permission_code)
);

CREATE INDEX IF NOT EXISTS idx_roles_slug ON roles (slug);

CREATE INDEX IF NOT EXISTS idx_permissions_module ON permissions (module);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions (role_id);

CREATE INDEX IF NOT EXISTS idx_role_permissions_perm ON role_permissions (permission_code);

-- Sembrado estructural de los 4 roles base para satisfacer llaves foráneas
INSERT INTO
    roles (
        role_id,
        name,
        slug,
        description,
        is_system,
        is_active
    )
VALUES (
        1,
        'Administrador General',
        'admin',
        'Control total y acceso irrestricto sobre todos los módulos operativos y de sistema.',
        TRUE,
        TRUE
    ),
    (
        2,
        'Agente de Ventas',
        'seller',
        'Gestión de cartera comercial, cotizaciones, pedidos asignados y seguimiento de clientes.',
        FALSE,
        TRUE
    ),
    (
        3,
        'Gerente de Mercadotecnia',
        'marketing',
        'Aprobación de pedidos, campañas, anuncios, supervisión comercial y atención al cliente.',
        FALSE,
        TRUE
    ),
    (
        4,
        'Operador de Bodega',
        'warehouse',
        'Surtido físico, revisión con lector láser, empaque por cajas maestras y control de stock.',
        FALSE,
        TRUE
    ) ON CONFLICT (role_id) DO
UPDATE
SET
    name = EXCLUDED.name,
    slug = EXCLUDED.slug,
    description = EXCLUDED.description,
    is_system = EXCLUDED.is_system;

SELECT setval (
        pg_get_serial_sequence ('roles', 'role_id'), COALESCE(
            (
                SELECT MAX(role_id)
                FROM roles
            ), 1
        )
    );

-- ============================================================================
-- 3. USUARIOS (users): ADAPTACIÓN A role_id Y LIMPIEZA DE COLUMNA role
-- ============================================================================
-- 3.1 Agregar role_id como FK
ALTER TABLE users
ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES roles (role_id) ON DELETE RESTRICT;

-- 3.2 Migrar datos de usuarios existentes según su texto en role
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'role'
    ) THEN
        -- Mapeo por coincidencia con el slug del rol
        UPDATE users u
        SET role_id = r.role_id
        FROM roles r
        WHERE u.role_id IS NULL 
          AND lower(trim(u.role)) = r.slug;

        -- Respaldo cruzado: si el usuario figura como gerente en groupmarketingmanagers, asegurar rol marketing (3)
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'groupmarketingmanagers') THEN
            UPDATE users u
            SET role_id = r.role_id
            FROM roles r
            WHERE r.slug = 'marketing'
              AND u.user_id IN (SELECT marketing_id FROM groupmarketingmanagers WHERE marketing_id IS NOT NULL)
              AND (u.role_id IS NULL OR u.role_id = 2);
        END IF;

        -- Fallback seguro: si algún usuario no tuvo coincidencia o era nulo, asignar vendedor (2)
        UPDATE users
        SET role_id = 2
        WHERE role_id IS NULL;

        -- Eliminar constraints, checks e índices viejos de role
        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
        ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;
        DROP INDEX IF EXISTS idx_users_role;

        -- Eliminar físicamente la columna legacy role
        ALTER TABLE users DROP COLUMN role CASCADE;
    END IF;
END $$;

-- 3.3 Asegurar NOT NULL en role_id e índice B-Tree
ALTER TABLE users ALTER COLUMN role_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_role_id ON users (role_id);

-- 3.4 Asegurar constraints e índices de users
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_user_id_positive'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT check_user_id_positive CHECK (user_id > 0);

END IF;

END $$;

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

CREATE INDEX IF NOT EXISTS idx_users_full_name_gin ON users USING gin (full_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_users_username_gin ON users USING gin (username gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_users_email_gin ON users USING gin (email gin_trgm_ops);

-- 3.5 Asegurar campos de bloqueo e intentos fallidos de login
ALTER TABLE users
ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP WITH TIME ZONE NULL;

CREATE INDEX IF NOT EXISTS idx_users_is_locked ON users (is_locked);

-- ============================================================================
-- 4. CLIENTES (customers) Y RECUPERACIÓN DE CONTRASEÑAS (password_resets)
-- ============================================================================
ALTER TABLE customers
ADD COLUMN IF NOT EXISTS agent_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS notificate BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP WITH TIME ZONE NULL;

CREATE INDEX IF NOT EXISTS idx_customers_is_locked ON customers (is_locked);

CREATE INDEX IF NOT EXISTS idx_customers_username ON customers (username);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email);

CREATE INDEX IF NOT EXISTS idx_customers_agent_id ON customers (agent_id);

CREATE INDEX IF NOT EXISTS idx_customers_full_name_gin ON customers USING gin (full_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_customers_username_gin ON customers USING gin (username gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_customers_email_gin ON customers USING gin (email gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_customers_updated_at ON customers (updated_at);

CREATE INDEX IF NOT EXISTS idx_customers_active ON customers (is_active);

-- Tabla password_resets
CREATE TABLE IF NOT EXISTS password_resets (
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

CREATE INDEX IF NOT EXISTS idx_password_resets_customer_id ON password_resets (customer_id);

CREATE INDEX IF NOT EXISTS idx_password_resets_user_id ON password_resets (user_id);

CREATE INDEX IF NOT EXISTS idx_password_resets_code ON password_resets (code);

-- ============================================================================
-- 5. GRUPOS COMERCIALES: UNIFICACIÓN UNIVERSAL EN group_users
--    Migra datos existentes desde groupmarketingmanagers, groupsellers y
--    users.sales_group_id antes de retirar las tablas/columnas legacy.
-- ============================================================================
CREATE TABLE IF NOT EXISTS group_users (
    sales_group_id INTEGER NOT NULL REFERENCES salesgroups (sales_group_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (sales_group_id, user_id)
);

-- Garantizar constraint único (sales_group_id, user_id) si la tabla ya existía sin PK compuesta
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'group_users'::regclass
          AND contype IN ('p', 'u')
          AND conkey @> ARRAY[
              (SELECT attnum FROM pg_attribute WHERE attrelid = 'group_users'::regclass AND attname = 'sales_group_id'),
              (SELECT attnum FROM pg_attribute WHERE attrelid = 'group_users'::regclass AND attname = 'user_id')
          ]
    ) THEN
        ALTER TABLE group_users ADD CONSTRAINT unique_group_user UNIQUE (sales_group_id, user_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_group_users_group ON group_users (sales_group_id);

CREATE INDEX IF NOT EXISTS idx_group_users_user ON group_users (user_id);

-- 5.1 Migrar gerentes de marketing existentes y garantizar role_id de marketing
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'groupmarketingmanagers') THEN
        UPDATE users u
        SET role_id = r.role_id
        FROM roles r
        WHERE r.slug = 'marketing'
          AND u.user_id IN (SELECT marketing_id FROM groupmarketingmanagers WHERE marketing_id IS NOT NULL)
          AND u.role_id = 2;

        INSERT INTO group_users (sales_group_id, user_id, assigned_at)
        SELECT sales_group_id, marketing_id, COALESCE(assigned_at, CURRENT_TIMESTAMP)
        FROM groupmarketingmanagers
        WHERE sales_group_id IS NOT NULL AND marketing_id IS NOT NULL
        ON CONFLICT (sales_group_id, user_id) DO NOTHING;
    END IF;
END $$;

-- 5.2 Migrar vendedores (sellers) existentes
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'groupsellers') THEN
        INSERT INTO group_users (sales_group_id, user_id, assigned_at)
        SELECT sales_group_id, seller_id, COALESCE(assigned_at, CURRENT_TIMESTAMP)
        FROM groupsellers
        WHERE sales_group_id IS NOT NULL AND seller_id IS NOT NULL
        ON CONFLICT (sales_group_id, user_id) DO NOTHING;
    END IF;
END $$;

-- 5.3 Migrar relación legacy users.sales_group_id si existiese en la base de datos
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'sales_group_id'
    ) THEN
        INSERT INTO group_users (sales_group_id, user_id)
        SELECT u.sales_group_id, u.user_id
        FROM users u
        WHERE u.sales_group_id IS NOT NULL
        ON CONFLICT (sales_group_id, user_id) DO NOTHING;

        ALTER TABLE users DROP COLUMN sales_group_id CASCADE;

END IF;

END $$;

-- 5.4 Eliminar tablas obsoletas tras migración exitosa
DROP TABLE IF EXISTS groupmarketingmanagers CASCADE;

DROP TABLE IF EXISTS groupsellers CASCADE;

-- ============================================================================
-- 6. PRODUCTOS (products): CAMPOS LOCK Y UBICACIÓN FÍSICA
-- ============================================================================
ALTER TABLE products
ADD COLUMN IF NOT EXISTS lock BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS location VARCHAR(50) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS display_priority INTEGER NOT NULL DEFAULT 1000000,
ADD COLUMN IF NOT EXISTS image_version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_products_lock ON products (lock);

CREATE INDEX IF NOT EXISTS idx_products_location ON products (location);

CREATE INDEX IF NOT EXISTS idx_products_display_priority ON products (display_priority ASC, product_id DESC);

CREATE INDEX IF NOT EXISTS idx_products_created_at ON products (created_at DESC);

-- ============================================================================
-- 6.1 LISTAS DE PRECIOS (pricelists): VISIBILIDAD PÚBLICA INTERNA Y STOREFRONT
-- ============================================================================
ALTER TABLE pricelists
ADD COLUMN IF NOT EXISTS is_public_internal BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_public_storefront BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_pricelists_public_internal ON pricelists (is_public_internal, is_active);
CREATE INDEX IF NOT EXISTS idx_pricelists_public_storefront ON pricelists (is_public_storefront, is_active);

-- Registro idempotente del permiso catalog.prices_public
INSERT INTO permissions (permission_code, module, name, description, depends_on)
VALUES (
    'catalog.prices_public',
    'pricing',
    'Ver Listas Públicas Internas',
    'Consulta de listas de precios mayoristas públicas internas con precios finales protegidos (sin costos base ni markups).',
    NULL
) ON CONFLICT (permission_code) DO NOTHING;

-- Asignación por defecto a rol admin y seller
INSERT INTO role_permissions (role_id, permission_code)
SELECT r.role_id, 'catalog.prices_public'
FROM roles r
WHERE r.slug IN ('admin', 'seller')
ON CONFLICT (role_id, permission_code) DO NOTHING;

-- ============================================================================
-- 7. PEDIDOS (orders) Y PARTIDAS (orderitems): CAMPOS DE ALMACÉN Y DESCUENTOS
-- ============================================================================
-- 7.1 Renombrar assigned_seller_id a assigned_user_id (unificación PBAC)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'assigned_seller_id'
    ) AND NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'assigned_user_id'
    ) THEN
        ALTER TABLE orders RENAME COLUMN assigned_seller_id TO assigned_user_id;

ELSIF EXISTS (
    SELECT
    FROM information_schema.columns
    WHERE
        table_name = 'orders'
        AND column_name = 'assigned_seller_id'
)
AND EXISTS (
    SELECT
    FROM information_schema.columns
    WHERE
        table_name = 'orders'
        AND column_name = 'assigned_user_id'
) THEN
UPDATE orders
SET
    assigned_user_id = assigned_seller_id
WHERE
    assigned_user_id IS NULL
    AND assigned_seller_id IS NOT NULL;

ALTER TABLE orders DROP COLUMN assigned_seller_id;

END IF;

END $$;

-- 7.2 Nuevas columnas de pedidos
ALTER TABLE orders
ADD COLUMN IF NOT EXISTS assigned_user_id INTEGER REFERENCES users (user_id),
ADD COLUMN IF NOT EXISTS invoice_type VARCHAR(50) NOT NULL DEFAULT 'factura',
ADD COLUMN IF NOT EXISTS sent_to_warehouse BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS warehouse_status VARCHAR(50) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS total_splits INTEGER NOT NULL DEFAULT 1,
ADD COLUMN IF NOT EXISTS warehouse_sent_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS warehouse_sent_by INTEGER REFERENCES users (user_id),
ADD COLUMN IF NOT EXISTS warehouse_show_details BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS audit_verdict VARCHAR(50) NOT NULL DEFAULT 'clean';

-- 7.3 Normalización y ajuste de constraints en orders
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_invoice_type_check;
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_warehouse_status_check;
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_audit_verdict_check;

ALTER TABLE orders ALTER COLUMN invoice_type TYPE VARCHAR(50);
ALTER TABLE orders ALTER COLUMN invoice_type SET DEFAULT 'factura';

ALTER TABLE orders ALTER COLUMN warehouse_status TYPE VARCHAR(50);
ALTER TABLE orders ALTER COLUMN warehouse_status DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN warehouse_status SET DEFAULT NULL;

ALTER TABLE orders ALTER COLUMN audit_verdict TYPE VARCHAR(50);
ALTER TABLE orders ALTER COLUMN audit_verdict SET DEFAULT 'clean';
UPDATE orders SET audit_verdict = 'clean' WHERE audit_verdict IS NULL;
ALTER TABLE orders ALTER COLUMN audit_verdict SET NOT NULL;

ALTER TABLE orders ALTER COLUMN total_splits SET DEFAULT 1;
UPDATE orders SET total_splits = 1 WHERE total_splits IS NULL OR total_splits = 0;

-- 7.4 Partidas de pedidos (orderitems): Descuentos aplicados
ALTER TABLE orderitems
ADD COLUMN IF NOT EXISTS discount_applied NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS discount_type VARCHAR(20) NOT NULL DEFAULT 'none';

ALTER TABLE orderitems ALTER COLUMN discount_type SET DEFAULT 'none';
UPDATE orderitems SET discount_type = 'none' WHERE discount_type IS NULL;

-- 7.5 Índices de pedidos
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders (assigned_user_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_warehouse_verdict ON orders (audit_verdict) WHERE sent_to_warehouse = TRUE;
CREATE INDEX IF NOT EXISTS idx_orders_warehouse_fifo ON orders (warehouse_sent_at ASC, order_id ASC) WHERE sent_to_warehouse = TRUE;
CREATE INDEX IF NOT EXISTS idx_orders_wh_status_fifo ON orders (warehouse_status, warehouse_sent_at ASC, order_id ASC) WHERE sent_to_warehouse = TRUE;

-- ============================================================================
-- 8. ECOSISTEMA DE ALMACÉN MODULAR (warehouse_containers, splits, items)
-- ============================================================================
-- 8.1 Contenedores / Canastas Físicas QR
CREATE TABLE IF NOT EXISTS warehouse_containers (
    container_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    qr_code VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available' CHECK (
        status IN (
            'available',
            'in_use',
            'quarantine',
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

-- Migración segura si container_id existía como integer en alguna base intermedia
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'warehouse_containers' 
          AND column_name = 'container_id' 
          AND data_type IN ('integer', 'smallint', 'bigint')
    ) THEN
        ALTER TABLE warehouse_splits DROP CONSTRAINT IF EXISTS warehouse_splits_active_container_id_fkey;
        ALTER TABLE warehouse_items DROP CONSTRAINT IF EXISTS warehouse_items_container_id_fkey;
        ALTER TABLE warehouse_container_items DROP CONSTRAINT IF EXISTS warehouse_container_items_container_id_fkey;
        ALTER TABLE warehouse_containers DROP CONSTRAINT IF EXISTS fk_containers_current_split;

        UPDATE warehouse_splits SET active_container_id = NULL WHERE active_container_id IS NOT NULL;
        UPDATE warehouse_items SET container_id = NULL WHERE container_id IS NOT NULL;
        DELETE FROM warehouse_container_items;
        DELETE FROM warehouse_containers;

        ALTER TABLE warehouse_containers ALTER COLUMN container_id DROP DEFAULT;
        ALTER TABLE warehouse_containers ALTER COLUMN container_id TYPE UUID USING gen_random_uuid();
        ALTER TABLE warehouse_containers ALTER COLUMN container_id SET DEFAULT gen_random_uuid();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_containers_qr ON warehouse_containers (qr_code);

CREATE INDEX IF NOT EXISTS idx_containers_status ON warehouse_containers (status);

CREATE INDEX IF NOT EXISTS idx_containers_split ON warehouse_containers (current_split_id);

-- 8.2 Lotes de Surtido y Revisión (warehouse_splits)
CREATE TABLE IF NOT EXISTS warehouse_splits (
    split_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    order_id BIGINT NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    split_number INTEGER NOT NULL,
    total_splits INTEGER NOT NULL DEFAULT 1,
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
    started_at TIMESTAMP WITH TIME ZONE,
    picking_completed_at TIMESTAMP WITH TIME ZONE,
    checking_started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    admin_override_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    admin_override_at TIMESTAMP WITH TIME ZONE,
    active_container_id UUID REFERENCES warehouse_containers (container_id) ON DELETE SET NULL,
    uses_containers BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_order_split UNIQUE (order_id, split_number)
);

-- Asegurar adaptación si warehouse_splits ya existía en base de datos intermedia
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'assigned_picker_id')
       AND NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'picker_id') THEN
        ALTER TABLE warehouse_splits RENAME COLUMN assigned_picker_id TO picker_id;
    END IF;

    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'assigned_checker_id')
       AND NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'checker_id') THEN
        ALTER TABLE warehouse_splits RENAME COLUMN assigned_checker_id TO checker_id;
    END IF;

    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'security_seal')
       AND NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'security_seal_folio') THEN
        ALTER TABLE warehouse_splits RENAME COLUMN security_seal TO security_seal_folio;
    END IF;

    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'check_started_at')
       AND NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_splits' AND column_name = 'checking_started_at') THEN
        ALTER TABLE warehouse_splits RENAME COLUMN check_started_at TO checking_started_at;
    END IF;
END $$;

ALTER TABLE warehouse_splits
ADD COLUMN IF NOT EXISTS total_splits INTEGER NOT NULL DEFAULT 1,
ADD COLUMN IF NOT EXISTS split_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS picker_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS checker_id INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS security_seal_folio VARCHAR(50),
ADD COLUMN IF NOT EXISTS checking_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS admin_override_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS admin_override_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS active_container_id UUID REFERENCES warehouse_containers (container_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS uses_containers BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE warehouse_splits 
SET split_code = order_id::text || '-S' || split_number::text 
WHERE split_code IS NULL;

ALTER TABLE warehouse_splits ALTER COLUMN split_code SET NOT NULL;
ALTER TABLE warehouse_splits ALTER COLUMN status TYPE VARCHAR(30);

ALTER TABLE warehouse_splits DROP CONSTRAINT IF EXISTS warehouse_splits_status_check;
ALTER TABLE warehouse_splits ADD CONSTRAINT warehouse_splits_status_check CHECK (
    status IN (
        'pending',
        'picking',
        'in_progress',
        'ready_for_check',
        'checking',
        'completed',
        'cancelled'
    )
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_containers_current_split'
    ) THEN
        ALTER TABLE warehouse_containers 
        ADD CONSTRAINT fk_containers_current_split 
        FOREIGN KEY (current_split_id) REFERENCES warehouse_splits (split_id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_splits_order_status ON warehouse_splits (order_id, status);
CREATE INDEX IF NOT EXISTS idx_splits_code ON warehouse_splits (split_code);
CREATE INDEX IF NOT EXISTS idx_splits_picker ON warehouse_splits (picker_id, status);
CREATE INDEX IF NOT EXISTS idx_splits_checker ON warehouse_splits (checker_id, status);
CREATE INDEX IF NOT EXISTS idx_splits_status ON warehouse_splits (status);
CREATE INDEX IF NOT EXISTS idx_splits_active_container ON warehouse_splits (active_container_id);
CREATE INDEX IF NOT EXISTS idx_splits_seal ON warehouse_splits (security_seal_folio) WHERE security_seal_folio IS NOT NULL;

-- 8.3 Partidas Granulares de Almacén (warehouse_items)
CREATE TABLE IF NOT EXISTS warehouse_items (
    warehouse_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    split_id UUID NOT NULL REFERENCES warehouse_splits (split_id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES orderitems (order_item_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id),
    container_id UUID REFERENCES warehouse_containers (container_id) ON DELETE SET NULL,
    required_quantity INTEGER NOT NULL CHECK (required_quantity > 0),
    picked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_scanned_qty >= 0),
    picked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (picked_boxes >= 0),
    picked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (picked_box_prods >= 0),
    picked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_manual_qty >= 0),
    picked_manual_reason VARCHAR(255) DEFAULT NULL,
    picked_total_qty INTEGER GENERATED ALWAYS AS (
        picked_scanned_qty + picked_box_prods + picked_manual_qty
    ) STORED,
    picked_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    picked_at TIMESTAMP WITH TIME ZONE,
    checked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_scanned_qty >= 0),
    checked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (checked_boxes >= 0),
    checked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (checked_box_prods >= 0),
    checked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_manual_qty >= 0),
    checked_manual_reason VARCHAR(255) DEFAULT NULL,
    checked_total_qty INTEGER GENERATED ALWAYS AS (
        checked_scanned_qty + checked_box_prods + checked_manual_qty
    ) STORED,
    checked_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    checked_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'partial', 'completed', 'discrepancy')
    ),
    admin_override_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    admin_override_at TIMESTAMP WITH TIME ZONE,
    admin_override_note TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Asegurar adaptación si warehouse_items ya existía en base de datos intermedia
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_items' AND column_name = 'quantity_requested')
       AND NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'warehouse_items' AND column_name = 'required_quantity') THEN
        ALTER TABLE warehouse_items RENAME COLUMN quantity_requested TO required_quantity;
    END IF;
END $$;

ALTER TABLE warehouse_items
ADD COLUMN IF NOT EXISTS required_quantity INTEGER NOT NULL DEFAULT 1 CHECK (required_quantity > 0),
ADD COLUMN IF NOT EXISTS picked_manual_reason VARCHAR(255) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS picked_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS picked_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS checked_manual_reason VARCHAR(255) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS checked_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS checked_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS admin_override_by INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS admin_override_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS admin_override_note TEXT DEFAULT NULL;

ALTER TABLE warehouse_items DROP CONSTRAINT IF EXISTS warehouse_items_status_check;
ALTER TABLE warehouse_items ADD CONSTRAINT warehouse_items_status_check CHECK (
    status IN ('pending', 'partial', 'completed', 'discrepancy')
);

CREATE INDEX IF NOT EXISTS idx_wh_items_split ON warehouse_items (split_id);
CREATE INDEX IF NOT EXISTS idx_wh_items_order_item ON warehouse_items (order_item_id);
CREATE INDEX IF NOT EXISTS idx_wh_items_product ON warehouse_items (product_id);
CREATE INDEX IF NOT EXISTS idx_wh_items_container ON warehouse_items (container_id);
CREATE INDEX IF NOT EXISTS idx_wh_items_status ON warehouse_items (status);

-- 8.4 Distribución Consolidada por Canasta Física (warehouse_container_items)
DROP TABLE IF EXISTS warehouse_scan_events CASCADE;

CREATE TABLE IF NOT EXISTS warehouse_container_items (
    container_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    split_id UUID NOT NULL REFERENCES warehouse_splits (split_id) ON DELETE CASCADE,
    container_id UUID NOT NULL REFERENCES warehouse_containers (container_id) ON DELETE CASCADE,
    warehouse_item_id UUID REFERENCES warehouse_items (warehouse_item_id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES orderitems (order_item_id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products (product_id),
    picked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_scanned_qty >= 0),
    picked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (picked_boxes >= 0),
    picked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (picked_box_prods >= 0),
    picked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (picked_manual_qty >= 0),
    picked_total_qty INTEGER GENERATED ALWAYS AS (
        picked_scanned_qty + picked_box_prods + picked_manual_qty
    ) STORED,
    checked_scanned_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_scanned_qty >= 0),
    checked_boxes INTEGER NOT NULL DEFAULT 0 CHECK (checked_boxes >= 0),
    checked_box_prods INTEGER NOT NULL DEFAULT 0 CHECK (checked_box_prods >= 0),
    checked_manual_qty INTEGER NOT NULL DEFAULT 0 CHECK (checked_manual_qty >= 0),
    checked_total_qty INTEGER GENERATED ALWAYS AS (
        checked_scanned_qty + checked_box_prods + checked_manual_qty
    ) STORED,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_split_container_product UNIQUE (
            split_id,
            container_id,
            product_id
        )
);

CREATE INDEX IF NOT EXISTS idx_wh_ci_split ON warehouse_container_items (split_id);

CREATE INDEX IF NOT EXISTS idx_wh_ci_container ON warehouse_container_items (container_id);

CREATE INDEX IF NOT EXISTS idx_wh_ci_item ON warehouse_container_items (warehouse_item_id);

CREATE INDEX IF NOT EXISTS idx_wh_ci_product ON warehouse_container_items (product_id);

CREATE INDEX IF NOT EXISTS idx_wh_ci_order_item ON warehouse_container_items (order_item_id);

-- ============================================================================
-- 9. TICKETS DE SOPORTE: ASOCIACIÓN CON PEDIDOS
-- ============================================================================
ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS order_id BIGINT REFERENCES orders (order_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_tickets_order_id ON tickets (order_id);

-- ============================================================================
-- 10. DESCUENTOS Y PROMOCIONES (product_discounts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_discounts (
    discount_id SERIAL PRIMARY KEY,
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
-- 11. ESTADÍSTICAS ANUALES POR PRODUCTO (product_yearly_stats)
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

-- Backfill histórico: calcular métricas a partir del historial real de pedidos completados
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

-- ============================================================================
-- 12. CONFIGURACIONES DEL SISTEMA (system_configs)
--     Estructura de la tabla (el sembrado de registros va en seed_system_configs.sql)
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
-- 13. APARTADOS TEMPORALES DE STOCK (order_stock_holds)
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

-- ============================================================================
-- 13.1 TABLAS DE COMUNICACIÓN Y AUDITORÍA (order_stats, announcements)
-- ============================================================================
CREATE TABLE IF NOT EXISTS order_stats (
    sales_group_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (sales_group_id, status)
);

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
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_send TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_announcements_active_lookup ON announcements (type, status, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_announcements_expiry ON announcements (status, end_date);
CREATE INDEX IF NOT EXISTS idx_announcements_created ON announcements (created_at DESC);

-- ============================================================================
-- 13.2 PUBLICIDAD DE INICIO (promo_ad_sections, promo_ad_items)
-- ============================================================================
CREATE TABLE IF NOT EXISTS promo_ad_sections (
    section_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES promo_ad_sections(section_id) ON DELETE CASCADE,
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

-- Permisos PBAC idempotentes para Publicidad de Inicio
INSERT INTO permissions (permission_code, module, name, description, depends_on)
VALUES
    ('promo_ads.view', 'promo_ads', 'Ver Publicidad de Inicio', 'Visualización y administración de los bloques publicitarios en la página de inicio.', NULL)
ON CONFLICT (permission_code) DO NOTHING;

INSERT INTO permissions (permission_code, module, name, description, depends_on)
VALUES
    ('promo_ads.create', 'promo_ads', 'Crear Publicidad de Inicio', 'Permite crear nuevas secciones (1 a 4 columnas) y anuncios publicitarios.', 'promo_ads.view'),
    ('promo_ads.edit', 'promo_ads', 'Editar Publicidad de Inicio', 'Permite modificar el orden, estado, enlaces e imágenes de publicidad de inicio.', 'promo_ads.view'),
    ('promo_ads.delete', 'promo_ads', 'Eliminar Publicidad de Inicio', 'Permite eliminar secciones y anuncios publicitarios junto con sus imágenes en S3.', 'promo_ads.view'),
    ('promo_ads.upload', 'promo_ads', 'Subir Imágenes de Publicidad', 'Habilita subir imágenes responsivas (desktop, tablet, móvil) de publicidad a S3.', 'promo_ads.view')
ON CONFLICT (permission_code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_code)
SELECT r.role_id, p.permission_code
FROM roles r
CROSS JOIN permissions p
WHERE (r.role_id = 1 OR r.slug = 'admin')
  AND p.module = 'promo_ads'
ON CONFLICT (role_id, permission_code) DO NOTHING;

-- ============================================================================
-- 14. LIMPIEZA DE ÍNDICES REDUNDANTES Y AJUSTE DE AUTOVACUUM
-- ============================================================================
DROP INDEX IF EXISTS idx_orders_seller;

DROP INDEX IF EXISTS idx_orders_seller_status;

DROP INDEX IF EXISTS idx_groupsellers_group;

DROP INDEX IF EXISTS idx_groupsellers_seller;

DROP INDEX IF EXISTS idx_groupmarketingmanagers_group;

DROP INDEX IF EXISTS idx_groupmarketingmanagers_marketing;

ALTER TABLE orders SET( autovacuum_vacuum_scale_factor = 0.05 );

ALTER TABLE cartcache SET( autovacuum_vacuum_scale_factor = 0.05 );

-- ============================================================================
-- 15. CONTROL DE SINCRONIZACIÓN ERP (COTIZA3)
-- ============================================================================
ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_synced BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_orders_is_synced ON orders (is_synced);

COMMIT;