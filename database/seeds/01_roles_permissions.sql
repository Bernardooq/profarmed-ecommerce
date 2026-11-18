-- ============================================================================
-- SCRIPT DE SEMBRADO (SEED): ROLES DINÁMICOS, CATÁLOGO DE PERMISOS Y MATRIZ
-- Base: profarmed-ecommerce / profarmed_api
-- Sincronizado 1:1 con PERMISSIONS_AND_CONSTRAINTS.md y permissions.js
-- ============================================================================

-- 1. TABLAS BASE DE PERMISOS Y ROLES (IF NOT EXISTS)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_code VARCHAR(100) PRIMARY KEY,
    module VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    depends_on VARCHAR(100) REFERENCES permissions(permission_code) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    permission_code VARCHAR(100) NOT NULL REFERENCES permissions(permission_code) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_code)
);

CREATE INDEX IF NOT EXISTS idx_roles_slug ON roles(slug);
CREATE INDEX IF NOT EXISTS idx_permissions_module ON permissions(module);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_perm ON role_permissions(permission_code);

-- ----------------------------------------------------------------------------
-- 2. SEMBRADO DE ROLES DEL SISTEMA (ROLES INTERNOS INICIALES)
-- ----------------------------------------------------------------------------
INSERT INTO roles (role_id, name, slug, description, is_system, is_active)
VALUES 
    (1, 'Administrador General', 'admin', 'Control total y acceso irrestricto sobre todos los módulos operativos y de sistema.', TRUE, TRUE),
    (2, 'Agente de Ventas', 'seller', 'Gestión de cartera comercial, cotizaciones, pedidos asignados y seguimiento de clientes.', FALSE, TRUE),
    (3, 'Gerente de Mercadotecnia', 'marketing', 'Aprobación de pedidos, campañas, anuncios, supervisión comercial y atención al cliente.', FALSE, TRUE),
    (4, 'Operador de Bodega', 'warehouse', 'Surtido físico, revisión con lector láser, empaque por cajas maestras y control de stock.', FALSE, TRUE)
ON CONFLICT (role_id) DO UPDATE 
SET 
    name = EXCLUDED.name,
    slug = EXCLUDED.slug,
    description = EXCLUDED.description,
    is_system = EXCLUDED.is_system;

-- Sincronizar secuencia si role_id serial quedó desfasado
SELECT setval(pg_get_serial_sequence('roles', 'role_id'), COALESCE((SELECT MAX(role_id) FROM roles), 1));

-- ----------------------------------------------------------------------------
-- 3. SEMBRADO DE CATÁLOGO MAESTRO DE PERMISOS (42 PERMISOS CANÓNICOS)
-- ----------------------------------------------------------------------------
-- Paso A: Insertar permisos raíz (sin dependencias directas primero)
INSERT INTO permissions (permission_code, module, name, description, depends_on)
VALUES
    -- Sistema
    ('system.admin', 'system', 'Administración Total (Superusuario)', 'Acceso maestro sin restricciones a todos los módulos, ajustes del sistema y overrides.', NULL),
    ('system.sync', 'system', 'Sincronizador FoxPro / ERP', 'Habilita la carga de archivos DBF para sincronizar precios, stock y catálogo con el ERP.', NULL),

    -- Usuarios
    ('users.view', 'users', 'Ver Directorio de Usuarios', 'Permite ver el directorio completo de colaboradores internos y todos los grupos comerciales sin restricción.', NULL),

    -- Anuncios
    ('announcements.view', 'announcements', 'Ver Anuncios y Banners', 'Visualización de campañas publicitarias activas, avisos y banners en el portal.', NULL),

    -- Publicidad de Inicio
    ('promo_ads.view', 'promo_ads', 'Ver Publicidad de Inicio', 'Visualización y administración de los bloques publicitarios en la página de inicio.', NULL),

    -- Pedidos
    ('orders.view', 'orders', 'Ver Pedidos Asignados (Bandeja Personal)', 'Permite ver y gestionar únicamente los pedidos asignados directamente a su propio usuario asesor (bandeja personal).', NULL),

    -- Almacén
    ('warehouse.view', 'warehouse', 'Ver Almacén y Surtido', 'Acceso a la pestaña Almacén, cola FIFO de surtido, historial de empaque y métricas operativas.', NULL),

    -- Inventario y Catálogo Físico (Raíz de Productos)
    ('catalog.view', 'products', 'Ver Inventario y Existencias', 'Acceso a la pestaña Inventario para consultar existencias físicas, stock en almacenes y catálogo general de productos.', NULL),

    -- Estrategia de Precios y Descuentos (Independiente de Stock)
    ('catalog.prices', 'pricing', 'Administrar Listas de Precios', 'Configuración de listas de precios mayoristas y márgenes porcentuales (markups) por segmento de cliente.', NULL),
    ('catalog.prices_public', 'pricing', 'Ver Listas Públicas Internas', 'Consulta de listas de precios mayoristas públicas internas con precios finales protegidos (sin costos base ni markups).', NULL),
    ('catalog.discounts', 'pricing', 'Administrar Descuentos', 'Creación de ofertas temporales, descuentos por volumen y promociones en productos.', NULL),

    -- Clientes
    ('customers.view', 'customers', 'Ver Clientes (Cartera Asignada)', 'Permite ver únicamente a los clientes pertenecientes a sus propios grupos de venta.', NULL),

    -- Grupos
    ('groups.view', 'groups', 'Ver Grupos Comerciales', 'Consulta de las unidades comerciales de venta, líderes y los asesores que las integran.', NULL),

    -- Contacto
    ('contact.view', 'contact', 'Ver Mensajes de Contacto', 'Consulta de mensajes enviados desde el formulario público de contacto del sitio web.', NULL),

    -- Soporte
    ('support.view', 'support', 'Ver Tickets de Soporte', 'Consulta de tickets e incidencias reportadas por clientes comerciales.', NULL),

    -- Reportes
    ('reports.view', 'reports', 'Ver Reportes y Dashboards', 'Acceso a la sección de reportes, gráficos ejecutivos y estadísticas comerciales.', NULL)
ON CONFLICT (permission_code) DO UPDATE
SET 
    module = EXCLUDED.module,
    name = EXCLUDED.name,
    description = EXCLUDED.description;

-- Paso B: Insertar permisos con dependencias hacia los permisos raíz
INSERT INTO permissions (permission_code, module, name, description, depends_on)
VALUES
    -- Usuarios
    ('users.create', 'users', 'Crear Usuarios Internos', 'Habilita dar de alta nuevas cuentas de empleados y colaboradores internos en la empresa.', 'users.view'),
    ('users.edit', 'users', 'Editar Usuarios Internos', 'Permite modificar nombres, teléfonos, restablecer contraseñas y activar o suspender colaboradores.', 'users.view'),
    ('users.delete', 'users', 'Eliminar / Desactivar Usuarios', 'Permite dar de baja o desactivar definitivamente cuentas de personal interno.', 'users.view'),
    ('roles.assign', 'users', 'Asignar Roles a Usuarios', 'Permite cambiar el rol asignado a un colaborador dentro del formulario de usuario.', 'users.view'),
    ('roles.view', 'users', 'Ver y Configurar Roles', 'Habilita la pantalla de administración de roles, creación de roles y personalización de permisos.', 'users.view'),

    -- Anuncios
    ('announcements.create', 'announcements', 'Crear Campañas de Anuncios', 'Habilita la publicación de nuevos banners promocionales, ventanas emergentes e historias.', 'announcements.view'),
    ('announcements.edit', 'announcements', 'Editar Anuncios', 'Modificar fechas de vigencia, enlaces destino y orden de visualización de anuncios.', 'announcements.view'),
    ('announcements.delete', 'announcements', 'Eliminar Campañas', 'Retirar definitivamente campañas de marketing y banners obsoletos.', 'announcements.view'),
    ('announcements.upload', 'announcements', 'Subir Creatividades e Imágenes', 'Habilita subir gráficos e imágenes publicitarias a los servidores en la nube.', 'announcements.view'),
    ('announcements.broadcast', 'announcements', 'Difusión Masiva por Correo', 'Habilita el envío automatizado de correos promocionales a toda la base de clientes.', 'announcements.view'),

    -- Publicidad de Inicio (Página de Inicio B2B)
    ('promo_ads.create', 'promo_ads', 'Crear Publicidad de Inicio', 'Permite crear nuevas secciones (1 a 4 columnas) y anuncios publicitarios.', 'promo_ads.view'),
    ('promo_ads.edit', 'promo_ads', 'Editar Publicidad de Inicio', 'Permite modificar el orden, estado, enlaces e imágenes de publicidad de inicio.', 'promo_ads.view'),
    ('promo_ads.delete', 'promo_ads', 'Eliminar Publicidad de Inicio', 'Permite eliminar secciones y anuncios publicitarios junto con sus imágenes en S3.', 'promo_ads.view'),
    ('promo_ads.upload', 'promo_ads', 'Subir Imágenes de Publicidad', 'Habilita subir imágenes responsivas (desktop, tablet, móvil) de publicidad a S3.', 'promo_ads.view'),

    -- Pedidos y Ventas
    ('orders.group_view', 'orders', 'Ver Pedidos de Grupos Comerciales', 'Permite ver los pedidos de todos los clientes pertenecientes a sus grupos de venta asignados (cartera de sucursal/equipo).', 'orders.view'),
    ('orders.create', 'orders', 'Crear Pedidos B2B', 'Habilita el botón "+ Crear Pedido" para levantar órdenes comerciales a clientes de su cartera.', 'orders.view'),
    ('catalog.customer_view', 'orders', 'Ver Precios B2B por Cliente', 'Permite consultar el catálogo simulando la lista de precios asignada a un cliente específico para cotizar y levantar pedidos.', 'orders.create'),
    ('orders.edit', 'orders', 'Editar Partidas y Pedidos', 'Permite agregar o modificar productos, cantidades y notas en pedidos antes de ser despachados.', 'orders.view'),
    ('orders.assign', 'orders', 'Reasignar Asesor Comercial', 'Permite reasignar el pedido a un asesor comercial distinto dentro de la empresa.', 'orders.view'),
    ('orders.status', 'orders', 'Cambiar Estados del Pedido', 'Permite avanzar fases generales del ciclo de vida del pedido en la máquina de estados.', 'orders.view'),
    ('orders.approve', 'orders', 'Aprobar Pedidos Comerciales', 'Habilita el botón "Aprobar" para autorizar pedidos pendientes y dejarlos listos para surtido o envío.', 'orders.view'),
    ('orders.ship', 'orders', 'Marcar Pedido como Enviado', 'Habilita el botón "Enviar" para despachar directamente el pedido a reparto o paquetería.', 'orders.view'),
    ('orders.deliver', 'orders', 'Marcar como Entregado', 'Habilita el botón "Entregar" al confirmar la recepción física exitosa por parte del cliente.', 'orders.view'),
    ('orders.cancel', 'orders', 'Cancelar Pedidos', 'Habilita el botón "Cancelar" solicitando el registro obligatorio de motivo justificado.', 'orders.view'),
    ('orders.export', 'orders', 'Exportar Pedidos a ERP', 'Habilita la descarga de pedidos en archivo TXT formateado para ingesta directa en el ERP central.', 'orders.view'),
    ('orders.view_all', 'orders', 'Ver TODOS los Pedidos (Global)', 'Permite ver todos los pedidos de la empresa a nivel nacional, sin limitación de grupo comercial.', 'orders.view'),

    -- Almacén
    ('warehouse.operator', 'warehouse', 'Surtidor de Bodega (1er Filtro)', 'Reclamar y operar el 1er filtro de surtido (Picker): escanear códigos de barras con pistola láser, cajas maestras y envío a revisión.', 'warehouse.view'),
    ('warehouse.checker', 'warehouse', 'Revisor de Bodega (2do Filtro)', 'Reclamar y operar el 2do filtro de revisión (Checker): escaneo cruzado de mercancía, validación ciega y colocación de sello de seguridad.', 'warehouse.view'),
    ('warehouse.send', 'warehouse', 'Enviar Pedidos a Bodega', 'Habilita derivar pedidos aprobados formalmente a la cola de surtido de bodega fragmentándolos en splits concurrentes.', 'warehouse.view'),
    ('warehouse.supervisor', 'warehouse', 'Supervisor de Logística y Tráfico', 'Habilita supervisar pedidos en bodega, reasignar lotes a personal y alternar modo ciego operativo (sin acceso a peritajes de discrepancias).', 'warehouse.view'),
    ('warehouse.audit', 'warehouse', 'Auditoría Forense de Calidad', 'Inspección forense de discrepancias entre Surtidor vs Revisor (piezas faltantes/sobrantes), sellos violados y dictamen pericial.', 'warehouse.view'),
    ('warehouse.manage', 'warehouse', 'Jefatura de Almacén y Override', 'Control maestro de bodega: visualización de discrepancias periciales, sobreescritura de conteos/sellos y forzado de estados.', 'warehouse.view'),
    ('warehouse.containers', 'warehouse', 'Administrar Contenedores Físicos QR', 'Alta, edición, desvinculación y asignación de códigos QR / etiquetas a contenedores y canastas de surtido.', 'warehouse.view'),
    ('warehouse.events', 'warehouse', 'Bitácora Atómica de Escaneos', 'Consulta de la bitácora inmutable de eventos de escaneo láser (código de barras, piezas, timestamp y terminal).', 'warehouse.view'),
    ('warehouse.filter2_send', 'warehouse', 'Enviar Split a 2do Filtro', 'Habilita transferir una split completada en piso a la mesa de control y calidad (segundo filtro).', 'warehouse.view'),
    ('warehouse.seal_direct', 'warehouse', 'Sellar y Finalizar Directo en Piso', 'Permite sellar con folio inviolable y concluir la split directamente desde piso tras el 1er filtro sin pasar por 2do filtro.', 'warehouse.view'),
    ('warehouse.mode_direct', 'warehouse', 'Activar Surtido Directo por Split', 'Permite seleccionar o alternar la modalidad de surtido directo por split (sin canastas físicas QR).', 'warehouse.view'),
    ('warehouse.mode_containers', 'warehouse', 'Activar Surtido con Canastas QR', 'Permite seleccionar o alternar la modalidad de recolección y trazabilidad con canastas físicas QR.', 'warehouse.view'),

    -- Inventario y Catálogo Físico (Productos y Existencias)
    ('catalog.categories', 'products', 'Administrar Categorías', 'Crear, renombrar y organizar las categorías terapéuticas y familias de productos.', 'catalog.view'),
    ('catalog.export', 'products', 'Exportar Inventario a Excel', 'Habilita la descarga de existencias, códigos de barra y productos del inventario en formato Excel.', 'catalog.view'),
    ('products.create', 'products', 'Crear Artículos en Inventario', 'Habilita registrar nuevos medicamentos o artículos dentro del catálogo de productos.', 'catalog.view'),
    ('products.edit', 'products', 'Editar Datos de Producto', 'Modificar nombre comercial, sustancias activas, claves de barra y descripción del producto.', 'catalog.view'),
    ('products.cost', 'products', 'Ver Costo Base e IVA ($)', 'Muestra el costo de compra confidencial (precio base) y tasa de IVA en el inventario.', 'catalog.view'),
    ('products.stock', 'products', 'Ajustar Stock Físico', 'Habilita la modificación manual de existencias físicas disponibles en los almacenes.', 'catalog.view'),
    ('products.manage', 'products', 'Ficha Técnica y Fiscal', 'Configurar laboratorio fabricante, ubicación física en anaquel, tasa de IVA y gravámenes.', 'catalog.view'),
    ('products.delete', 'products', 'Eliminar Productos', 'Permite eliminar del catálogo productos que nunca hayan sido incluidos en ningún pedido.', 'products.manage'),
    ('products.images', 'products', 'Subir Fotos a la Nube', 'Habilita subir fotografías de productos con optimización automática WebP a CloudFront/S3.', 'products.manage'),

    -- Clientes
    ('customers.create', 'customers', 'Registrar Clientes B2B', 'Habilita el alta directa de nuevos clientes mayoristas y farmacias en la plataforma.', 'customers.view'),
    ('customers.edit', 'customers', 'Editar Datos de Clientes', 'Modificar razones sociales, RFC, correo fiscal y datos generales de contacto.', 'customers.view'),
    ('customers.delete', 'customers', 'Desactivar Clientes', 'Baja lógica de clientes que no posean compras activas ni saldo pendiente.', 'customers.view'),
    ('customers.addresses_edit', 'customers', 'Gestionar Sucursales de Entrega', 'Agregar y actualizar domicilios secundarios y sucursales de entrega del cliente.', 'customers.view'),
    ('customers.requests_view', 'customers', 'Ver Solicitudes de Alta', 'Auditoría de prospectos registrados en el buzón web para apertura de cuenta comercial.', 'customers.view'),
    ('customers.requests_download', 'customers', 'Descargar Expedientes Fiscales', 'Generar enlaces temporales para descargar documentación fiscal en PDF (CSF, INE, Comprobante).', 'customers.requests_view'),
    ('customers.requests_manage', 'customers', 'Aprobar Solicitudes de Alta', 'Habilita dar el visto bueno o rechazar solicitudes de prospectos para convertirlos en clientes activos.', 'customers.requests_view'),
    ('customers.assign', 'customers', 'Reasignar Cartera de Clientes', 'Transferir clientes comerciales entre diferentes agentes de ventas.', 'customers.view'),
    ('customers.view_all', 'customers', 'Ver TODOS los Clientes (Global)', 'Permite consultar a todos los clientes de la empresa a nivel nacional sin importar su grupo.', 'customers.view'),

    -- Grupos
    ('groups.manage', 'groups', 'Administrar Equipos de Venta', 'Crear nuevos grupos comerciales, asignar gerentes y vincular vendedores a equipos.', 'groups.view'),

    -- Contacto
    ('contact.manage', 'contact', 'Gestionar Mensajes Web', 'Marcar mensajes como atendidos, enviar respuestas por correo y descartar mensajes.', 'contact.view'),

    -- Soporte
    ('support.create', 'support', 'Crear Tickets de Ayuda', 'Permite abrir un nuevo ticket de atención o reclamo vinculado a un pedido.', 'support.view'),
    ('support.reply', 'support', 'Responder a Clientes', 'Permite redactar respuestas y dar seguimiento en la conversación del ticket.', 'support.view'),
    ('support.manage', 'support', 'Gestionar Mesa de Ayuda', 'Tomar tickets, cambiar estatus (Abierto, En Proceso, Resuelto) y reasignar operadores.', 'support.view'),
    ('support.deescalate', 'support', 'Desescalar Incidencias', 'Regresar un ticket escalado a la atención operativa habitual.', 'support.manage'),

    -- Reportes
    ('reports.sales', 'reports', 'Reporte Financiero Detallado', 'Acceso a costos de venta, utilidades brutas y márgenes porcentuales por período y producto.', 'reports.view'),
    ('reports.financial', 'reports', 'Métricas Financieras del Dashboard', 'Muestra ingresos anuales, utilidades netas acumuladas y gráficos de tendencia de facturación.', 'reports.view'),
    ('reports.export', 'reports', 'Exportar Reportes', 'Habilita la descarga de informes de rendimiento y balances en PDF y hojas de cálculo.', 'reports.view')
ON CONFLICT (permission_code) DO UPDATE
SET 
    module = EXCLUDED.module,
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    depends_on = EXCLUDED.depends_on;

-- ----------------------------------------------------------------------------
-- 4. MATRIZ DE PERMISOS POR ROL INICIAL (ROLE_PERMISSIONS)
-- ----------------------------------------------------------------------------

-- A. ADMIN: Todos los permisos existentes
INSERT INTO role_permissions (role_id, permission_code)
SELECT 1, permission_code FROM permissions
ON CONFLICT (role_id, permission_code) DO NOTHING;

-- B. MARKETING (Gerente de Mercadotecnia)
INSERT INTO role_permissions (role_id, permission_code)
VALUES 
    (3, 'reports.view'),
    (3, 'orders.view'),
    (3, 'orders.group_view'),
    (3, 'orders.create'),
    (3, 'orders.status'),
    (3, 'orders.approve'),
    (3, 'warehouse.view'),
    (3, 'warehouse.send'),
    (3, 'warehouse.supervisor'),
    (3, 'warehouse.audit'),
    (3, 'warehouse.containers'),
    (3, 'warehouse.events'),
    (3, 'warehouse.filter2_send'),
    (3, 'warehouse.seal_direct'),
    (3, 'warehouse.mode_direct'),
    (3, 'warehouse.mode_containers'),
    (3, 'support.view'),
    (3, 'support.create'),
    (3, 'support.reply'),
    (3, 'support.manage'),
    (3, 'catalog.view'),
    (3, 'catalog.customer_view'),
    (3, 'customers.view'),
    (3, 'groups.view')
ON CONFLICT (role_id, permission_code) DO NOTHING;

-- C. SELLER (Agente de Ventas)
INSERT INTO role_permissions (role_id, permission_code)
VALUES 
    (2, 'reports.view'),
    (2, 'orders.view'),
    (2, 'orders.create'),
    (2, 'orders.status'),
    (2, 'catalog.customer_view'),
    (2, 'catalog.prices_public'),
    (2, 'customers.view'),
    (2, 'groups.view'),
    (2, 'support.view'),
    (2, 'support.create')
ON CONFLICT (role_id, permission_code) DO NOTHING;

-- D. WAREHOUSE (Operador de Bodega y Segundo Filtro)
INSERT INTO role_permissions (role_id, permission_code)
VALUES 
    (4, 'warehouse.view'),
    (4, 'warehouse.operator'),
    (4, 'warehouse.checker'),
    (4, 'warehouse.containers'),
    (4, 'warehouse.filter2_send'),
    (4, 'warehouse.seal_direct'),
    (4, 'warehouse.mode_direct'),
    (4, 'warehouse.mode_containers'),
    (4, 'support.view'),
    (4, 'support.create')
ON CONFLICT (role_id, permission_code) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 5. MIGRACIÓN EN users: ASIGNAR role_id Y ELIMINAR COLUMNA role
-- ----------------------------------------------------------------------------
-- 5.1 Asegurar que la columna role_id exista en users
ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES roles(role_id) ON DELETE RESTRICT;
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);

-- 5.2 Mapear usuarios existentes según su valor de role
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'role'
    ) THEN
        -- Mapear por coincidencia con slug
        UPDATE users u
        SET role_id = r.role_id
        FROM roles r
        WHERE u.role_id IS NULL 
          AND lower(trim(u.role)) = r.slug;

        -- Fallback a seller (2) si algún usuario no tuvo coincidencia o era nulo
        UPDATE users
        SET role_id = 2
        WHERE role_id IS NULL;

        -- Asegurar constraint NOT NULL
        ALTER TABLE users ALTER COLUMN role_id SET NOT NULL;

        -- Eliminar constraints y checks sobre role
        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
        ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;
        DROP INDEX IF EXISTS idx_users_role;

        -- Eliminar físicamente la columna role
        ALTER TABLE users DROP COLUMN role CASCADE;
    END IF;
END $$;
