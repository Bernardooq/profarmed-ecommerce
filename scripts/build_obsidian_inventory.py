import os, ast, re

def inspect_py(path):
    functions = []
    classes = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=path)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
    except Exception:
        pass
    return classes, functions

def inspect_js(path):
    symbols = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Named function declarations
        funcs = re.findall(r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(', code)
        
        # Arrow function consts
        const_arrows = re.findall(r'(?:export\s+)?const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>', code)
        
        # Object methods inside service objects
        obj_methods = re.findall(r'^\s*(?:async\s+)?([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{', code, re.MULTILINE)
        obj_methods = [m for m in obj_methods if m not in ('if', 'for', 'while', 'switch', 'catch')]
        
        # Collect and deduplicate
        combined = funcs + const_arrows + obj_methods
        seen = set()
        for s in combined:
            if s not in seen and not s.startswith('_'):
                seen.add(s)
                symbols.append(s)
    except Exception:
        pass
    return symbols

def get_node_details(rel):
    b = os.path.basename(rel)
    parts = rel.split('/')
    
    # Database
    if 'database' in parts:
        if b == '01_init.sql':
            return {
                'desc': 'Script DDL PostgreSQL maestro v2 (esquema completo, índices GIN pg_trgm, FKs en cascada)',
                'tables': ['users', 'customers', 'salesgroups', 'products', 'pricelists', 'orders', 'warehouse_splits', 'orderitems', 'order_item_split_fulfillment', 'cartcache', 'product_discounts', 'product_yearly_stats', 'tickets', 'announcements'],
                'role': 'DDL Init'
            }
        if b == 'legacy_init.sql':
            return {
                'desc': 'Esquema base histórico/legacy de producción previo a la introducción de splits, promociones e invoice_type',
                'tables': ['users', 'customers', 'orders', 'orderitems', 'cartcache', 'pricelists', 'customerinfo'],
                'role': 'Legacy Reference'
            }
        if b == '001_consolidated.sql':
            return {
                'desc': 'Migración consolidada e idempotente (splits, group_users, product_yearly_stats, order_stock_holds, roles y is_synced)',
                'tables': ['warehouse_splits', 'group_users', 'orders', 'orderitems', 'product_discounts', 'product_yearly_stats', 'roles'],
                'role': 'Migration Pipeline'
            }
        if b in ('001_backfill_group_users.sql', '002_recalculate_yearly_stats.sql'):
            return {
                'desc': f'Parche histórico/manual de migración ({b})',
                'tables': ['group_users', 'product_yearly_stats'],
                'role': 'Migration Patch'
            }
        if b == '01_roles_permissions.sql':
            return {
                'desc': 'Catálogo maestro de 75 permisos PBAC y matriz inicial de 4 roles (admin, seller, marketing, warehouse)',
                'tables': ['roles', 'permissions', 'role_permissions', 'users'],
                'role': 'PBAC Seed'
            }
        if b == '02_system_configs.sql':
            return {
                'desc': 'Semilla idempotente de banderas globales operativas en system_configs',
                'tables': ['system_configs'],
                'role': 'Config Seed'
            }
        if b == 'sync_check.sql':
            return {
                'desc': 'Consultas de diagnóstico para validar consistencia de sincronización ERP y marcas temporales',
                'tables': ['products', 'pricelists', 'customers'],
                'role': 'DB Verification'
            }

    # Backend
    if 'backend' in parts:
        classes, funcs = inspect_py(rel)
        if 'routes' in parts:
            entity = b.replace('.py', '')
            return {
                'desc': f'Endpoints REST FastAPI para /{entity}',
                'routes_entity': entity,
                'funcs': funcs,
                'classes': classes,
                'role': 'API Router'
            }
        if 'crud' in parts:
            entity = b.replace('crud_', '').replace('.py', '')
            return {
                'desc': f'Capa CRUD de acceso a datos y lógica transaccional para {entity}',
                'entity': entity,
                'funcs': funcs,
                'classes': classes,
                'role': 'CRUD Engine'
            }
        if 'schemas' in parts:
            entity = b.replace('.py', '')
            return {
                'desc': f'Esquemas Pydantic (Request/Response DTOs) para {entity}',
                'entity': entity,
                'classes': classes,
                'funcs': funcs,
                'role': 'Data Contract'
            }
        if 'db' in parts:
            if b == 'base.py':
                return {
                    'desc': 'Modelos ORM declarativos de SQLAlchemy (User, Customer, Order, OrderItem, Product, WarehouseSplit, etc.)',
                    'classes': classes,
                    'role': 'ORM Models'
                }
            if b == 'session.py':
                return {
                    'desc': 'Motor de base de datos SQLAlchemy, pool de conexiones y generador get_db()',
                    'funcs': funcs,
                    'role': 'DB Engine'
                }
        if 'core' in parts:
            return {
                'desc': f'Módulo core ({b}): configuración, seguridad JWT o blacklist de tokens',
                'funcs': funcs,
                'classes': classes,
                'role': 'Core System'
            }
        return {
            'desc': f'Módulo backend de soporte ({b})',
            'funcs': funcs,
            'classes': classes,
            'role': 'Backend Utility'
        }

    # Frontend
    if 'react' in parts:
        symbols = inspect_js(rel)
        if 'pages' in parts:
            page_name = b.split('.')[0]
            return {
                'desc': f'Vista SPA de página completa para {page_name}',
                'page': page_name,
                'symbols': symbols[:8],
                'role': 'View Page'
            }
        if 'components' in parts:
            comp_name = b.split('.')[0]
            cat = parts[parts.index('components') + 1] if len(parts) > parts.index('components') + 1 else 'ui'
            return {
                'desc': f'Componente UI ({cat}): {comp_name}',
                'symbols': symbols[:8],
                'role': f'UI Component ({cat})'
            }
        if 'context' in parts:
            ctx_name = b.split('.')[0]
            return {
                'desc': f'Contexto de React y proveedor de estado para {ctx_name}',
                'symbols': symbols,
                'role': 'State Context'
            }
        if 'services' in parts:
            svc_name = b.split('.')[0]
            return {
                'desc': f'Cliente API y llamadas HTTP para {svc_name}',
                'symbols': symbols,
                'role': 'API Client'
            }
        if 'utils' in parts:
            return {
                'desc': f'Funciones utilitarias y helpers ({b})',
                'symbols': symbols,
                'role': 'Helper Utility'
            }
        return {
            'desc': f'Recurso frontend ({b})',
            'symbols': symbols[:6],
            'role': 'Frontend Resource'
        }

    return {
        'desc': f'Módulo ({b})',
        'role': 'General Module'
    }

# Build map
domains = [
    {
        'id': 'orders-cart',
        'title': '📦 Dominio 1: Carrito, Checkout y Pedidos (Orders & Cart)',
        'description': 'Flujo completo de pedidos desde la adición al carrito temporal (`cartcache`), checkout cliente/interno (`orders`, `orderitems`), cálculo de impuestos/descuentos, edición administrativa y auditoría.',
        'database': ['database/schema/01_init.sql', 'database/migrations/001_consolidated.sql', 'database/schema/legacy_init.sql'],
        'models': ['backend/profarmed_api/db/base.py'],
        'schemas': ['backend/profarmed_api/schemas/order.py', 'backend/profarmed_api/schemas/order_direct.py', 'backend/profarmed_api/schemas/order_edit.py', 'backend/profarmed_api/schemas/cart.py'],
        'crud': ['backend/profarmed_api/crud/crud_order.py', 'backend/profarmed_api/crud/crud_order_edit.py', 'backend/profarmed_api/crud/crud_cart.py', 'backend/profarmed_api/crud/crud_order_stats.py'],
        'routes': ['backend/profarmed_api/routes/orders.py'],
        'frontend_context': ['react/src/context/CartContext.jsx'],
        'frontend_services': ['react/src/services/orderService.js', 'react/src/services/cartService.js'],
        'frontend_pages': ['react/src/pages/Cart.jsx', 'react/src/pages/Orders.jsx', 'react/src/pages/AllOrders.jsx'],
        'frontend_components': [
            'react/src/components/orders/OrderModal.jsx',
            'react/src/components/modals/orders/ModalCreateOrder.jsx',
            'react/src/components/modals/orders/ModalEditOrder.jsx',
            'react/src/components/modals/orders/ModalOrderDetails.jsx',
            'react/src/components/orders/OrderHistory.jsx',
            'react/src/components/cart/CartItemList.jsx',
            'react/src/components/cart/CartSummary.jsx'
        ]
    },
    {
        'id': 'warehouse',
        'title': '🏭 Dominio 2: Almacén, Splits y Surtido (Warehouse Fulfillment)',
        'description': 'Módulo de bodegas y surtido: división de órdenes en splits (`warehouse_splits`), verificación de doble filtro (`order_item_split_fulfillment`: Picker & Checker), sellos de seguridad y veredictos forenses (`audit_verdict`).',
        'database': ['database/schema/01_init.sql', 'database/migrations/001_consolidated.sql'],
        'models': ['backend/profarmed_api/db/base.py'],
        'schemas': ['backend/profarmed_api/schemas/warehouse.py'],
        'crud': [
            'backend/profarmed_api/crud/crud_warehouse.py',
            'backend/profarmed_api/crud/crud_warehouse_orders.py',
            'backend/profarmed_api/crud/crud_warehouse_operations.py',
            'backend/profarmed_api/crud/crud_warehouse_audit.py',
            'backend/profarmed_api/crud/crud_warehouse_status.py'
        ],
        'routes': ['backend/profarmed_api/routes/warehouse.py'],
        'frontend_services': ['react/src/services/warehouseService.js'],
        'frontend_pages': ['react/src/pages/UnifiedDashboard.jsx', 'react/src/pages/WarehouseOrders.jsx'],
        'frontend_components': [
            'react/src/components/warehouse/ModalReassignSplit.jsx',
            'react/src/components/warehouse/ModalScanSplit.jsx',
            'react/src/components/warehouse/ModalWarehouseAudit.jsx',
            'react/src/components/warehouse/SplitDetailModal.jsx',
            'react/src/components/warehouse/WarehouseFIFOQueue.jsx',
            'react/src/components/warehouse/WarehouseStatsCards.jsx'
        ]
    },
    {
        'id': 'catalog-pricing',
        'title': '🏷️ Dominio 3: Catálogo, Precios, Descuentos y Recomendaciones',
        'description': 'Gestión de productos (`products`, `location`), categorías, listas de precios con markups (`pricelists`, `pricelistitems`), promociones vigentes (`product_discounts`), estadísticas anuales (`product_yearly_stats`) y productos similares.',
        'database': ['database/schema/01_init.sql', 'database/migrations/001_consolidated.sql'],
        'models': ['backend/profarmed_api/db/base.py'],
        'schemas': ['backend/profarmed_api/schemas/product.py', 'backend/profarmed_api/schemas/category.py', 'backend/profarmed_api/schemas/price_list.py', 'backend/profarmed_api/schemas/discount.py'],
        'crud': [
            'backend/profarmed_api/crud/crud_catalog.py',
            'backend/profarmed_api/crud/crud_product.py',
            'backend/profarmed_api/crud/crud_category.py',
            'backend/profarmed_api/crud/crud_price_list.py',
            'backend/profarmed_api/crud/crud_discount.py',
            'backend/profarmed_api/crud/crud_product_yearly_stats.py'
        ],
        'routes': ['backend/profarmed_api/routes/catalog.py', 'backend/profarmed_api/routes/categories.py', 'backend/profarmed_api/routes/products.py', 'backend/profarmed_api/routes/price_lists.py', 'backend/profarmed_api/routes/discounts.py'],
        'frontend_services': ['react/src/services/catalogService.js', 'react/src/services/priceListService.js', 'react/src/services/discountService.js'],
        'frontend_pages': ['react/src/pages/Catalog.jsx', 'react/src/pages/ProductDetail.jsx'],
        'frontend_components': [
            'react/src/components/products/ProductCard.jsx',
            'react/src/components/products/ProductGrid.jsx',
            'react/src/components/products/InventoryManager.jsx',
            'react/src/components/admin/DiscountsManager.jsx',
            'react/src/components/admin/PriceListManager.jsx'
        ]
    },
    {
        'id': 'users-customers-sales',
        'title': '👥 Dominio 4: Usuarios, Clientes, Vendedores y Grupos de Venta (RBAC / PBAC)',
        'description': 'Estructura comercial y permisos: administración de staff interno (`users`, `roles`, `permissions`, `role_permissions`), clientes con RFC y múltiples direcciones (`customers`, `customerinfo`), y asignación grupal (`salesgroups`, `groupsellers`, `groupmarketingmanagers`).',
        'database': ['database/schema/01_init.sql', 'database/seeds/01_roles_permissions.sql', 'database/schema/legacy_init.sql'],
        'models': ['backend/profarmed_api/db/base.py'],
        'schemas': ['backend/profarmed_api/schemas/user.py', 'backend/profarmed_api/schemas/role.py', 'backend/profarmed_api/schemas/customer.py', 'backend/profarmed_api/schemas/sales_group.py', 'backend/profarmed_api/schemas/auth.py'],
        'crud': [
            'backend/profarmed_api/crud/crud_user.py',
            'backend/profarmed_api/crud/crud_role.py',
            'backend/profarmed_api/crud/crud_customer.py',
            'backend/profarmed_api/crud/crud_commercial_group.py'
        ],
        'routes': ['backend/profarmed_api/routes/auth.py', 'backend/profarmed_api/routes/admin.py', 'backend/profarmed_api/routes/users.py', 'backend/profarmed_api/routes/roles.py', 'backend/profarmed_api/routes/commercial_groups.py', 'backend/profarmed_api/routes/customers.py', 'backend/profarmed_api/routes/dashboards.py'],
        'frontend_context': ['react/src/context/AuthContext.jsx', 'react/src/hooks/usePermissions.js', 'react/src/config/permissions.js'],
        'frontend_services': ['react/src/services/authService.js', 'react/src/services/adminService.js', 'react/src/services/userService.js', 'react/src/services/salesGroupService.js', 'react/src/services/customerService.js', 'react/src/services/dashboardService.js'],
        'frontend_pages': ['react/src/pages/Login.jsx', 'react/src/pages/UnifiedDashboard.jsx'],
        'frontend_components': [
            'react/src/components/admin/ClientManagement.jsx',
            'react/src/components/admin/RolesManagement.jsx',
            'react/src/components/admin/RoleFormModal.jsx',
            'react/src/components/admin/SalesTeamManagement.jsx',
            'react/src/components/common/RoleGate.jsx'
        ]
    },
    {
        'id': 'support-announcements',
        'title': '🎫 Dominio 5: Soporte (Tickets), Anuncios y Mensajería',
        'description': 'Módulos transversales de interacción: sistema de tickets con hilos de chat y vinculación a órdenes (`tickets`, `ticket_messages`), banners emergentes e historias (`announcements`), solicitudes fiscales (`client_requests`) y contacto (`contact_messages`).',
        'database': ['database/schema/01_init.sql'],
        'models': ['backend/profarmed_api/db/base.py'],
        'schemas': ['backend/profarmed_api/schemas/ticket.py', 'backend/profarmed_api/schemas/announcement.py'],
        'crud': [
            'backend/profarmed_api/crud/crud_ticket.py',
            'backend/profarmed_api/crud/crud_announcement.py',
            'backend/profarmed_api/crud/crud_contact_client.py'
        ],
        'routes': ['backend/profarmed_api/routes/tickets.py', 'backend/profarmed_api/routes/announcement.py', 'backend/profarmed_api/routes/public_announcement.py', 'backend/profarmed_api/routes/contact.py', 'backend/profarmed_api/routes/client_request.py'],
        'frontend_services': ['react/src/services/ticketService.js', 'react/src/services/announcementService.js'],
        'frontend_pages': ['react/src/pages/Support.jsx'],
        'frontend_components': [
            'react/src/components/tickets/TicketCreateModal.jsx',
            'react/src/components/tickets/TicketDashboard.jsx',
            'react/src/components/tickets/TicketThread.jsx',
            'react/src/components/announcements/StoriesBar.jsx',
            'react/src/components/announcements/PopupBanner.jsx',
            'react/src/components/announcements/FooterBanner.jsx'
        ]
    },
    {
        'id': 'erp-sync',
        'title': '🔄 Dominio 6: Sincronización ERP (DBF Files & Background Sync)',
        'description': 'Scripts y servicios de sincronización multihilo para importar archivos `.DBF` de catálogo, usuarios y listas de precios desde sistemas contables locales hacia la API.',
        'database': ['database/schema/01_init.sql'],
        'crud': ['backend/profarmed_api/crud/crud_sync_batch.py', 'backend/profarmed_api/crud/crud_sync_upload.py'],
        'routes': ['backend/profarmed_api/routes/sync_batch.py', 'backend/profarmed_api/routes/sync_upload.py'],
        'sync_modules': [
            'sync_local/src/uploader/sync_all_batch.py',
            'sync_local/src/uploader/sync_all_zip.py',
            'sync_local/src/uploader/sync_products_zip.py',
            'sync_alpha/src/uploader/sync_all_zip.py'
        ]
    }
]

lines = [
    '# Base de Conocimiento y Grafo de Arquitectura (RAG & Fast Navigation)',
    '',
    '> **Propósito**: Índice semántico de navegación ultrarrápida para IA y desarrolladores. Permite localizar de inmediato las capas de código (Database -> ORM -> Schema -> CRUD -> Router -> Service -> Component -> View) involucradas en cualquier cambio, sin necesidad de escanear o leer archivos uno por uno.',
    '',
    '## 🧭 Matriz de Navegación por Dominio (Full-Stack Vertical Slices)',
    ''
]

for d in domains:
    title = d['title']
    desc = d['description']
    lines.append(f'### {title}')
    lines.append(f'*{desc}*')
    lines.append('')
    lines.append('| Capa Arquitectónica | Archivos Wiki-Link | Responsabilidad Clave |')
    lines.append('|---|---|---|')
    
    for key, label in [
        ('database', '🗄️ Database / DDL'),
        ('models', '🧱 ORM Models'),
        ('schemas', '📋 Pydantic DTOs'),
        ('crud', '⚙️ CRUD / Lógica BD'),
        ('routes', '🌐 API Routes (FastAPI)'),
        ('frontend_context', '🧠 State Context'),
        ('frontend_services', '📡 API Clients'),
        ('frontend_pages', '🖥️ Views / Pages'),
        ('frontend_components', '🧩 UI Components'),
        ('sync_modules', '🔄 Sync Pipeline')
    ]:
        if key in d:
            files_links = []
            sample_desc = ''
            for f in d[key]:
                info = get_node_details(f)
                sample_desc = info.get('desc', '')
                symbols_snippet = ''
                if 'funcs' in info and info['funcs']:
                    symbols_snippet = f' <br>*(f: {", ".join(info["funcs"][:4])})*'
                elif 'classes' in info and info['classes']:
                    symbols_snippet = f' <br>*(c: {", ".join(info["classes"][:3])})*'
                elif 'symbols' in info and info['symbols']:
                    symbols_snippet = f' <br>*(sym: {", ".join(info["symbols"][:4])})*'
                files_links.append(f'[[{f}]]{symbols_snippet}')
            lines.append(f'| **{label}** | {"<br>".join(files_links)} | {sample_desc} |')
    lines.append('')

lines.extend([
    '---',
    '',
    '## 📚 Índice de Nodos del Proyecto (Directorio Completo)',
    ''
])

all_sections = [
    ('Database & Migraciones', 'database', ('.sql',)),
    ('Backend (FastAPI, SQLAlchemy, Pydantic)', 'backend', ('.py',)),
    ('Frontend (React, Vite, Estilos)', 'react', ('.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.html')),
    ('Scripts & Sincronización ERP', ('scripts', 'sync_alpha', 'sync_local'), ('.py', '.js', '.sh', '.bat', '.ps1'))
]

for title, root_filter, exts in all_sections:
    items = []
    roots = [root_filter] if isinstance(root_filter, str) else list(root_filter)
    for r in roots:
        if not os.path.exists(r): continue
        for root, dirs, files in os.walk(r):
            dirs[:] = [d for d in dirs if d not in ('venv', 'node_modules', 'dist', '.vite', '.git', '__pycache__', '.pytest_cache')]
            for f in sorted(files):
                if f.endswith(exts):
                    rel = os.path.relpath(os.path.join(root, f), '.').replace('\\', '/')
                    items.append(rel)
    items.sort()
    lines.append(f'### {title} ({len(items)} archivos)')
    lines.append('')
    for item in items:
        info = get_node_details(item)
        desc = info.get('desc', 'Archivo del proyecto')
        sym_list = []
        if 'funcs' in info and info['funcs']: sym_list.extend(info['funcs'][:5])
        if 'classes' in info and info['classes']: sym_list.extend(info['classes'][:3])
        if 'symbols' in info and info['symbols']: sym_list.extend(info['symbols'][:5])
        if sym_list:
            lines.append(f'- [[{item}]] — **{info.get("role", "Module")}**: {desc} `[{", ".join(sym_list)}]`')
        else:
            lines.append(f'- [[{item}]] — **{info.get("role", "Module")}**: {desc}')
    lines.append('')

output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'file_inventory.md')
with open(output_path, 'w', encoding='utf-8') as out:
    out.write('\n'.join(lines))

print(f'File inventory reescrito como Base de Conocimiento RAG de alta fidelidad en: {output_path}')
