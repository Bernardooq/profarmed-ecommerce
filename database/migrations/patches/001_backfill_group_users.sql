-- ============================================================================
-- SCRIPT DE MIGRACIÓN: Unificación de grupos a group_users
-- Base: profarmed-ecommerce / profarmed_api (Profarmed, Profarmed, Demo)
--
-- Ejecútalo en la base de datos previa/legacy para migrar de forma segura
-- las relaciones de 'groupmarketingmanagers' y 'groupsellers' hacia 'group_users'
-- SIN perder ningún vendedor ni gerente de marketing asociado a los grupos.
-- ============================================================================

BEGIN;

-- 1. Crear tabla unificada group_users si no existe
CREATE TABLE IF NOT EXISTS group_users (
    sales_group_id INTEGER NOT NULL REFERENCES salesgroups (sales_group_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sales_group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_group_users_user ON group_users (user_id);

-- 2. Migrar gerentes de marketing existentes
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'groupmarketingmanagers') THEN
        INSERT INTO group_users (sales_group_id, user_id, assigned_at)
        SELECT sales_group_id, marketing_id, assigned_at
        FROM groupmarketingmanagers
        ON CONFLICT (sales_group_id, user_id) DO NOTHING;
        
        RAISE NOTICE 'Datos de groupmarketingmanagers migrados exitosamente a group_users.';
    END IF;
END $$;

-- 3. Migrar vendedores (sellers) existentes
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'groupsellers') THEN
        INSERT INTO group_users (sales_group_id, user_id, assigned_at)
        SELECT sales_group_id, seller_id, assigned_at
        FROM groupsellers
        ON CONFLICT (sales_group_id, user_id) DO NOTHING;
        
        RAISE NOTICE 'Datos de groupsellers migrados exitosamente a group_users.';
    END IF;
END $$;

-- 4. Eliminar las tablas viejas una vez respaldada la información
DROP TABLE IF EXISTS groupmarketingmanagers CASCADE;
DROP TABLE IF EXISTS groupsellers CASCADE;

COMMIT;
