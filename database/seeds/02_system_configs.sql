-- ============================================================================
-- SCRIPT DE SEMILLA / POBLADO: Configuraciones Iniciales del Sistema
-- ============================================================================
-- Se asignan IDs con rango espaciado (100+) o bien específicos para dejar
-- los IDs iniciales (1-99) a configuraciones centrales de autenticación o núcleo.
-- Por petición se dejan listos con IDs 101 y 102 (o configurables) con is_active = FALSE.

INSERT INTO
    system_configs (
        config_id,
        config_name,
        description,
        is_active,
        created_at,
        updated_at
    )
VALUES (
        101,
        'order.apartar',
        'Aparta provisionalmente el stock de los productos al crear pedidos web hasta que se aprueben o sincronicen con el ERP SAI.',
        FALSE,
        NOW(),
        NOW()
    ),
    (
        102,
        'order.discount',
        'Descuenta inmediatamente las existencias del catálogo web en cuanto se crea un pedido antes del proceso en almacén/SAI.',
        FALSE,
        NOW(),
        NOW()
    ),
    (
        103,
        'catalog.order_by_priority',
        'Prioriza en el catálogo y filtros por defecto los productos con display_priority manual (1 a 999,999) y después los generales.',
        TRUE,
        NOW(),
        NOW()
    ),
    (
        104,
        'catalog.weekly_rotation',
        'Habilita la rotación y barajado periódico de productos sin prioridad personalizada (>= 1,000,000) para dar variedad visual al cliente.',
        FALSE,
        NOW(),
        NOW()
    ),
    (
        105,
        'user.auto_create_sales_group',
        'Crea automáticamente un grupo de ventas vinculado al registrar o sincronizar un nuevo colaborador/usuario interno.',
        TRUE,
        NOW(),
        NOW()
    ),
    (
        106,
        'customer.auto_assign_agent_group',
        'Asigna automáticamente al cliente al grupo comercial de su agente/vendedor asignado al crear, actualizar o sincronizar.',
        TRUE,
        NOW(),
        NOW()
    ),
    (
        107,
        'pricing.tax_inclusive',
        'Indica que los precios de listas ya incluyen IVA (modelo neto mostrador/farmacia). Al estar activo, no suma IVA adicional en catálogo ni checkout y desglosa el impuesto hacia abajo.',
        FALSE,
        NOW(),
        NOW()
    ) ON CONFLICT (config_id) DO
UPDATE
SET
    config_name = EXCLUDED.config_name,
    description = EXCLUDED.description,
    updated_at = NOW();