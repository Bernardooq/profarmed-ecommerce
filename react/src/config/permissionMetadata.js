/**
 * Metadatos descriptivos y UX/UI para el Catálogo Maestro de Permisos (PBAC).
 * Proporciona nombres claros, etiquetas de acción ("Qué botón o capacidad desbloquea"),
 * badges de alcance (Global vs Cartera) y resúmenes concisos sin ambigüedades.
 */

export const PERMISSION_METADATA = {
  // ============================================================================
  // 1. USUARIOS Y ADMINISTRACIÓN CENTRAL (users)
  // ============================================================================
  'users.view': {
    label: 'Ver Directorio de Usuarios',
    actionTag: 'Directorio y Equipos',
    scope: 'Lectura Global',
    description: 'Permite ver el directorio completo de colaboradores internos y todos los grupos comerciales sin restricción.'
  },
  'users.create': {
    label: 'Crear Usuarios Internos',
    actionTag: 'Botón "+ Nuevo Usuario"',
    scope: 'Administración',
    description: 'Habilita dar de alta nuevas cuentas de empleados y colaboradores internos en la empresa.'
  },
  'users.edit': {
    label: 'Editar Usuarios Internos',
    actionTag: 'Botón "Editar Usuario"',
    scope: 'Administración',
    description: 'Permite modificar nombres, teléfonos, restablecer contraseñas y activar o suspender colaboradores.'
  },
  'users.delete': {
    label: 'Eliminar / Desactivar Usuarios',
    actionTag: 'Botón "Desactivar"',
    scope: 'Administración',
    description: 'Permite dar de baja o desactivar definitivamente cuentas de personal interno.'
  },
  'roles.assign': {
    label: 'Asignar Roles a Usuarios',
    actionTag: 'Selector de Roles',
    scope: 'Seguridad PBAC',
    description: 'Permite cambiar el rol asignado a un colaborador dentro del formulario de usuario.'
  },
  'roles.view': {
    label: 'Ver y Configurar Roles',
    actionTag: 'Pestaña Roles y Matriz',
    scope: 'Seguridad PBAC',
    description: 'Habilita la pantalla de administración de roles, creación de roles y personalización de permisos.'
  },

  // ============================================================================
  // 2. PEDIDOS Y VENTAS (orders)
  // ============================================================================
  'orders.view': {
    label: 'Ver Pedidos Asignados (Bandeja Personal)',
    actionTag: 'Pedidos Asignados a Mí',
    scope: 'Asignación Directa',
    description: 'Permite acceder a Pedidos y ver únicamente los pedidos asignados directamente a su propio usuario asesor (bandeja personal).'
  },
  'orders.group_view': {
    label: 'Ver Pedidos de Grupos Comerciales',
    actionTag: 'Cartera de Sucursal/Equipo',
    scope: 'Grupos Comerciales',
    description: 'Permite ver los pedidos de todos los clientes pertenecientes a sus grupos de venta asignados (visibilidad de equipo/sucursal).'
  },
  'orders.view_all': {
    label: 'Ver TODOS los Pedidos (Global)',
    actionTag: 'Visibilidad Global Nacional',
    scope: 'Acceso Irrestricto',
    description: 'Permite ver todos los pedidos de la empresa a nivel nacional, sin limitación de grupo comercial ni asesor.'
  },
  'orders.create': {
    label: 'Crear Pedidos B2B',
    actionTag: 'Botón "+ Crear Pedido"',
    scope: 'Operativo Ventas',
    description: 'Habilita el botón "+ Crear Pedido" para levantar órdenes comerciales a clientes de su cartera.'
  },
  'catalog.customer_view': {
    label: 'Ver Precios B2B por Cliente',
    actionTag: 'Precios Mayoristas B2B',
    scope: 'Comercial B2B',
    description: 'Permite consultar el catálogo simulando la lista de precios asignada a un cliente específico para cotizar y levantar pedidos.'
  },
  'orders.edit': {
    label: 'Editar Partidas y Pedidos',
    actionTag: 'Botón "Editar Pedido"',
    scope: 'Operativo Ventas',
    description: 'Permite agregar o modificar productos, cantidades y notas en pedidos antes de ser despachados.'
  },
  'orders.assign': {
    label: 'Reasignar Asesor Comercial',
    actionTag: 'Selector de Asesor',
    scope: 'Supervisión Comercial',
    description: 'Permite reasignar el pedido a un asesor comercial distinto dentro de la empresa.'
  },
  'orders.status': {
    label: 'Cambiar Estados del Pedido',
    actionTag: 'Máquina de Estados',
    scope: 'Operativo',
    description: 'Permite avanzar fases generales del ciclo de vida del pedido en la máquina de estados.'
  },
  'orders.approve': {
    label: 'Aprobar Pedidos Comerciales',
    actionTag: 'Botón "Aprobar"',
    scope: 'Autorización Comercial',
    description: 'Habilita el botón "Aprobar" para autorizar pedidos pendientes y dejarlos listos para surtido o envío.'
  },
  'orders.ship': {
    label: 'Marcar Pedido como Enviado',
    actionTag: 'Botón "Enviar"',
    scope: 'Despacho Directo',
    description: 'Habilita el botón "Enviar" para despachar directamente el pedido a reparto o paquetería.'
  },
  'orders.deliver': {
    label: 'Marcar como Entregado',
    actionTag: 'Botón "Entregar"',
    scope: 'Comprobación Entrega',
    description: 'Habilita el botón "Entregar" al confirmar la recepción física exitosa por parte del cliente.'
  },
  'orders.cancel': {
    label: 'Cancelar Pedidos',
    actionTag: 'Botón "Cancelar"',
    scope: 'Cancelación',
    description: 'Habilita el botón "Cancelar" solicitando el registro obligatorio de motivo justificado.'
  },
  'orders.export': {
    label: 'Exportar Pedidos a ERP',
    actionTag: 'Botón "Exportar ERP"',
    scope: 'Integración FoxPro',
    description: 'Habilita la descarga de pedidos en archivo TXT formateado para ingesta directa en el ERP central.'
  },

  // ============================================================================
  // 3. ALMACÉN Y SURTIDO (warehouse)
  // ============================================================================
  'warehouse.view': {
    label: 'Ver Almacén y Surtido',
    actionTag: 'Pestaña Almacén y Colas FIFO',
    scope: 'Consulta Operativa',
    description: 'Acceso a la pestaña Almacén, cola FIFO de surtido, historial de empaque y métricas operativas generales.'
  },
  'warehouse.operator': {
    label: 'Surtidor de Bodega (1er Filtro)',
    actionTag: 'Pistola Láser: Surtido (Picker)',
    scope: 'Piso — 1er Filtro',
    description: 'Reclamar y operar el 1er filtro de surtido (Picker): escanear códigos de barras con pistola láser, cajas maestras y envío a revisión.'
  },
  'warehouse.checker': {
    label: 'Revisor de Bodega (2do Filtro)',
    actionTag: 'Pistola Láser: Revisión (Checker)',
    scope: 'Piso — 2do Filtro',
    description: 'Reclamar y operar el 2do filtro de revisión (Checker): escaneo cruzado de mercancía, validación ciega y colocación de sello de seguridad.'
  },
  'warehouse.send': {
    label: 'Enviar Pedidos a Bodega',
    actionTag: 'Botón "📦 A Bodega"',
    scope: 'Logística y Tráfico',
    description: 'Habilita derivar pedidos aprobados formalmente a la cola de surtido de bodega fragmentándolos en splits concurrentes.'
  },
  'warehouse.supervisor': {
    label: 'Supervisor de Logística y Tráfico',
    actionTag: 'Supervisión y Reasignación',
    scope: 'Supervisión de Turno',
    description: 'Habilita reasignar lotes a personal y alternar modo ciego operativo (sin acceso a peritajes de discrepancias).'
  },
  'warehouse.audit': {
    label: 'Auditoría Forense de Calidad',
    actionTag: 'Peritaje Forense y Discrepancias',
    scope: 'Control de Calidad (QA)',
    description: 'Inspección forense de discrepancias entre Surtidor vs Revisor (piezas faltantes/sobrantes), sellos violados y dictamen pericial.'
  },
  'warehouse.manage': {
    label: 'Jefatura de Almacén y Override',
    actionTag: 'Override Conteos, Discrepancias y Sellos',
    scope: 'Jefatura Integral',
    description: 'Control maestro de bodega: visualización de discrepancias periciales, sobreescritura de conteos/sellos y forzado de estados.'
  },
  'warehouse.containers': {
    label: 'Administrar Contenedores Físicos QR',
    actionTag: 'Gestión de Canastas y Splits',
    scope: 'Operación Logística',
    description: 'Alta, edición, desvinculación y asignación de códigos QR / etiquetas a contenedores y canastas de surtido.'
  },
  'warehouse.events': {
    label: 'Bitácora Atómica de Escaneos',
    actionTag: 'Event Ledger Forense',
    scope: 'Auditoría y Trazabilidad',
    description: 'Consulta de la bitácora inmutable de eventos de escaneo láser (código de barras, piezas, timestamp y terminal).'
  },
  'warehouse.filter2_send': {
    label: 'Enviar Split a 2do Filtro',
    actionTag: 'Botón "🔍 Enviar a 2do Filtro"',
    scope: 'Control de Calidad / Piso',
    description: 'Habilita transferir una split completada en piso a la mesa de control y calidad (segundo filtro).'
  },
  'warehouse.seal_direct': {
    label: 'Sellar y Finalizar Directo en Piso',
    actionTag: 'Botón "🔒 Sellar Split (Directo)"',
    scope: 'Piso — Cierre Inviolable',
    description: 'Permite sellar con folio inviolable y concluir la split directamente desde piso tras el 1er filtro sin pasar por 2do filtro.'
  },
  'warehouse.mode_direct': {
    label: 'Activar Surtido Directo por Split',
    actionTag: 'Botón "📦 Pasar a Surtido Directo"',
    scope: 'Modalidad Operativa',
    description: 'Permite seleccionar o alternar la modalidad de surtido directo por split (sin canastas físicas QR).'
  },
  'warehouse.mode_containers': {
    label: 'Activar Surtido con Canastas QR',
    actionTag: 'Botón "🧺 Usar Canastas QR"',
    scope: 'Modalidad Operativa',
    description: 'Permite seleccionar o alternar la modalidad de recolección y trazabilidad con canastas físicas QR.'
  },

  // ============================================================================
  // 4. INVENTARIO Y CATÁLOGO FÍSICO (products)
  // ============================================================================
  'catalog.view': {
    label: 'Ver Inventario y Existencias',
    actionTag: 'Pestaña Inventario',
    scope: 'Consulta General',
    description: 'Acceso a la pestaña Inventario para consultar existencias físicas, stock en almacenes y catálogo general de productos.'
  },
  'products.create': {
    label: 'Crear Artículos en Inventario',
    actionTag: 'Botón "+ Nuevo Producto"',
    scope: 'Inventario',
    description: 'Habilita registrar nuevos medicamentos o artículos dentro del catálogo de productos.'
  },
  'products.edit': {
    label: 'Editar Datos de Producto',
    actionTag: 'Botón "Editar Producto"',
    scope: 'Inventario',
    description: 'Modificar nombre comercial, sustancias activas, claves de barra y descripción del producto.'
  },
  'products.stock': {
    label: 'Ajustar Stock Físico',
    actionTag: 'Edición Manual de Stock',
    scope: 'Bodega / Stock',
    description: 'Habilita la modificación manual de existencias físicas disponibles en los almacenes.'
  },
  'products.cost': {
    label: 'Ver Costo Base e IVA ($)',
    actionTag: 'Costo Confidencial e IVA',
    scope: 'Confidencial / Financiero',
    description: 'Muestra el costo de compra confidencial (precio base) y la tasa de IVA en el inventario. Los márgenes y markups se gestionan en Listas de Precios.'
  },
  'catalog.categories': {
    label: 'Administrar Categorías',
    actionTag: 'Familias y Categorías',
    scope: 'Catálogo',
    description: 'Crear, renombrar y organizar las categorías terapéuticas y familias de productos dentro del inventario.'
  },
  'catalog.export': {
    label: 'Exportar Inventario a Excel',
    actionTag: 'Botón "Exportar Excel"',
    scope: 'Descargas',
    description: 'Habilita la descarga de existencias, códigos de barra y productos del inventario en formato Excel.'
  },
  'products.manage': {
    label: 'Ficha Técnica y Fiscal',
    actionTag: 'Laboratorio, Anaquel e IVA',
    scope: 'Inventario',
    description: 'Configurar laboratorio fabricante, ubicación física en anaquel, tasa de IVA y gravámenes.'
  },
  'products.delete': {
    label: 'Eliminar Productos',
    actionTag: 'Botón "Eliminar Producto"',
    scope: 'Inventario',
    description: 'Permite eliminar del catálogo productos que nunca hayan sido incluidos en ningún pedido.'
  },
  'products.images': {
    label: 'Subir Fotos a la Nube',
    actionTag: 'Carga de Fotos WebP',
    scope: 'Multimedia',
    description: 'Habilita subir fotografías de productos con optimización automática WebP a CloudFront/S3.'
  },

  // ============================================================================
  // 5. ESTRATEGIA DE PRECIOS Y PROMOCIONES (pricing)
  // ============================================================================
  'catalog.prices': {
    label: 'Administrar Listas de Precios',
    actionTag: 'Pestaña Precios y Markups',
    scope: 'Estrategia Precios',
    description: 'Configuración de listas de precios mayoristas y márgenes porcentuales (markups) por segmento de cliente.'
  },
  'catalog.prices_public': {
    label: 'Ver Listas Públicas Internas',
    actionTag: 'Pestaña Precios (Lectura)',
    scope: 'Precios Protegidos',
    description: 'Consulta de listas de precios mayoristas públicas internas con precios finales protegidos (sin costos base ni markups).'
  },
  'catalog.discounts': {
    label: 'Administrar Descuentos',
    actionTag: 'Pestaña Ofertas y Descuentos',
    scope: 'Promociones',
    description: 'Creación de ofertas temporales, descuentos por volumen y promociones en productos.'
  },

  // ============================================================================
  // 6. CLIENTES B2B Y CARTERA (customers)
  // ============================================================================
  'customers.view': {
    label: 'Ver Clientes (Cartera Asignada)',
    actionTag: 'Cartera Asignada',
    scope: 'Grupos Asignados',
    description: 'Permite ver únicamente a los clientes pertenecientes a sus propios grupos de venta.'
  },
  'customers.view_all': {
    label: 'Ver TODOS los Clientes (Global)',
    actionTag: 'Cartera Nacional Completa',
    scope: 'Acceso Irrestricto',
    description: 'Permite consultar a todos los clientes de la empresa a nivel nacional sin importar su grupo.'
  },
  'customers.create': {
    label: 'Registrar Clientes B2B',
    actionTag: 'Botón "+ Nuevo Cliente"',
    scope: 'Comercial',
    description: 'Habilita el alta directa de nuevos clientes mayoristas y farmacias en la plataforma.'
  },
  'customers.edit': {
    label: 'Editar Datos de Clientes',
    actionTag: 'Botón "Editar Cliente"',
    scope: 'Comercial',
    description: 'Modificar razones sociales, RFC, correo fiscal y datos generales de contacto.'
  },
  'customers.delete': {
    label: 'Desactivar Clientes',
    actionTag: 'Botón "Desactivar Cliente"',
    scope: 'Comercial',
    description: 'Baja lógica de clientes que no posean compras activas ni saldo pendiente.'
  },
  'customers.addresses_edit': {
    label: 'Gestionar Sucursales de Entrega',
    actionTag: 'Direcciones de Entrega',
    scope: 'Logística Clientes',
    description: 'Agregar y actualizar domicilios secundarios y sucursales de entrega del cliente.'
  },
  'customers.assign': {
    label: 'Reasignar Cartera de Clientes',
    actionTag: 'Botón "Asignar Asesor"',
    scope: 'Coordinación Ventas',
    description: 'Transferir clientes comerciales entre diferentes agentes de ventas.'
  },
  'customers.requests_view': {
    label: 'Ver Solicitudes de Alta',
    actionTag: 'Buzón "Quiero ser Cliente"',
    scope: 'Prospección',
    description: 'Auditoría de prospectos registrados en el buzón web para apertura de cuenta comercial.'
  },
  'customers.requests_download': {
    label: 'Descargar Expedientes Fiscales',
    actionTag: 'Descarga de CSF, INE y Aviso',
    scope: 'Auditoría Fiscal',
    description: 'Generar enlaces temporales para descargar documentación fiscal en PDF (CSF, INE, Comprobante).'
  },
  'customers.requests_manage': {
    label: 'Aprobar Solicitudes de Alta',
    actionTag: 'Botón "Aprobar Prospecto"',
    scope: 'Alta Comercial',
    description: 'Habilita dar el visto bueno o rechazar solicitudes de prospectos para convertirlos en clientes activos.'
  },

  // ============================================================================
  // 7. GRUPOS COMERCIALES DE VENTA (groups)
  // ============================================================================
  'groups.view': {
    label: 'Ver Grupos Comerciales',
    actionTag: 'Equipos de Venta',
    scope: 'Estructura Comercial',
    description: 'Consulta de las unidades comerciales de venta, líderes y los asesores que las integran.'
  },
  'groups.manage': {
    label: 'Administrar Equipos de Venta',
    actionTag: 'Crear y Asignar Equipos',
    scope: 'Estructura Comercial',
    description: 'Crear nuevos grupos comerciales, asignar gerentes y vincular vendedores a equipos.'
  },

  // ============================================================================
  // 8. ANUNCIOS Y PROMOCIONES (announcements)
  // ============================================================================
  'announcements.view': {
    label: 'Ver Anuncios y Banners',
    actionTag: 'Campañas y Banners',
    scope: 'Marketing',
    description: 'Visualización de campañas publicitarias activas, avisos y banners en el portal.'
  },
  'announcements.create': {
    label: 'Crear Campañas de Anuncios',
    actionTag: 'Botón "+ Nuevo Anuncio"',
    scope: 'Marketing',
    description: 'Habilita la publicación de nuevos banners promocionales, ventanas emergentes e historias.'
  },
  'announcements.edit': {
    label: 'Editar Anuncios',
    actionTag: 'Botón "Editar Anuncio"',
    scope: 'Marketing',
    description: 'Modificar fechas de vigencia, enlaces destino y orden de visualización de anuncios.'
  },
  'announcements.delete': {
    label: 'Eliminar Campañas',
    actionTag: 'Botón "Eliminar Anuncio"',
    scope: 'Marketing',
    description: 'Retirar definitivamente campañas de marketing y banners obsoletos.'
  },
  'announcements.upload': {
    label: 'Subir Creatividades e Imágenes',
    actionTag: 'Carga de Imágenes a S3',
    scope: 'Multimedia',
    description: 'Habilita subir gráficos e imágenes publicitarias a los servidores en la nube.'
  },
  'announcements.broadcast': {
    label: 'Difusión Masiva por Correo',
    actionTag: 'Envío Masivo de E-mails',
    scope: 'Marketing Masivo',
    description: 'Habilita el envío automatizado de correos promocionales a toda la base de clientes.'
  },

  // ============================================================================
  // 8.1 PUBLICIDAD DE INICIO (promo_ads)
  // ============================================================================
  'promo_ads.view': {
    label: 'Ver Publicidad de Inicio',
    actionTag: 'Pestaña "Publicidad Inicio"',
    scope: 'Marketing B2B',
    description: 'Visualización y administración de los bloques publicitarios en la página de inicio.'
  },
  'promo_ads.create': {
    label: 'Crear Publicidad de Inicio',
    actionTag: 'Botones "+ Nueva Sección" / "+ Anuncio"',
    scope: 'Marketing B2B',
    description: 'Permite crear nuevas secciones (1 a 4 columnas) y agregar anuncios/carruseles por cuadro.'
  },
  'promo_ads.edit': {
    label: 'Editar Publicidad de Inicio',
    actionTag: 'Editar, Reordenar y Activar',
    scope: 'Marketing B2B',
    description: 'Permite modificar orden, vigencia, estado, enlaces e imágenes de secciones y anuncios.'
  },
  'promo_ads.delete': {
    label: 'Eliminar Publicidad de Inicio',
    actionTag: 'Botón "Eliminar"',
    scope: 'Marketing B2B',
    description: 'Permite eliminar secciones y anuncios publicitarios junto con sus imágenes en S3.'
  },
  'promo_ads.upload': {
    label: 'Subir Imágenes de Publicidad',
    actionTag: 'Carga WebP Responsiva a S3',
    scope: 'Multimedia',
    description: 'Habilita subir imágenes responsivas (Desktop, Tablet y Móvil) de publicidad a S3.'
  },

  // ============================================================================
  // 9. REPORTES Y ANALÍTICA (reports)
  // ============================================================================
  'reports.view': {
    label: 'Ver Reportes y Dashboards',
    actionTag: 'Dashboards y Gráficos',
    scope: 'Analítica General',
    description: 'Acceso a la sección de reportes, gráficos ejecutivos y estadísticas comerciales.'
  },
  'reports.financial': {
    label: 'Métricas Financieras del Dashboard',
    actionTag: 'Ingresos y Tendencias Anuales',
    scope: 'Finanzas / Dirección',
    description: 'Muestra ingresos anuales, utilidades netas acumuladas y gráficos de tendencia de facturación.'
  },
  'reports.sales': {
    label: 'Reporte Financiero Detallado',
    actionTag: 'Costos, Ganancia y Margen %',
    scope: 'Finanzas / Rentabilidad',
    description: 'Acceso a costos de venta, utilidades brutas y márgenes porcentuales por período y producto.'
  },
  'reports.export': {
    label: 'Exportar Reportes',
    actionTag: 'Botón "Descargar PDF / Excel"',
    scope: 'Exportación',
    description: 'Habilita la descarga de informes de rendimiento y balances en PDF y hojas de cálculo.'
  },

  // ============================================================================
  // 10. TICKETS Y SOPORTE (support)
  // ============================================================================
  'support.view': {
    label: 'Ver Tickets de Soporte',
    actionTag: 'Mesa de Ayuda',
    scope: 'Atención a Clientes',
    description: 'Consulta de tickets e incidencias reportadas por clientes comerciales.'
  },
  'support.create': {
    label: 'Crear Tickets de Ayuda',
    actionTag: 'Botón "+ Nuevo Ticket"',
    scope: 'Atención a Clientes',
    description: 'Permite abrir un nuevo ticket de atención o reclamo vinculado a un pedido.'
  },
  'support.reply': {
    label: 'Responder a Clientes',
    actionTag: 'Enviar Respuestas',
    scope: 'Atención a Clientes',
    description: 'Permite redactar respuestas y dar seguimiento en la conversación del ticket.'
  },
  'support.manage': {
    label: 'Gestionar Mesa de Ayuda',
    actionTag: 'Asignar y Cerrar Tickets',
    scope: 'Mesa de Ayuda',
    description: 'Tomar tickets, cambiar estatus (Abierto, En Proceso, Resuelto) y reasignar operadores.'
  },
  'support.deescalate': {
    label: 'Desescalar Incidencias',
    actionTag: 'Retornar a Operación Regular',
    scope: 'Mesa de Ayuda',
    description: 'Regresar un ticket escalado a la atención operativa habitual.'
  },

  // ============================================================================
  // 11. MENSAJES DE CONTACTO (contact)
  // ============================================================================
  'contact.view': {
    label: 'Ver Mensajes de Contacto',
    actionTag: 'Bandeja de Entrada Web',
    scope: 'Atención Prospectos',
    description: 'Consulta de mensajes enviados desde el formulario público de contacto del sitio web.'
  },
  'contact.manage': {
    label: 'Gestionar Mensajes Web',
    actionTag: 'Atender, Responder o Borrar',
    scope: 'Atención Prospectos',
    description: 'Marcar mensajes como atendidos, enviar respuestas por correo y descartar mensajes.'
  },

  // ============================================================================
  // 12. SISTEMA CENTRAL Y ERP (system)
  // ============================================================================
  'system.admin': {
    label: 'Administración Total (Superusuario)',
    actionTag: 'Control Maestro Irrestricto',
    scope: 'Superusuario',
    description: 'Acceso maestro sin restricciones a todos los módulos, ajustes del sistema y overrides.'
  },
  'system.sync': {
    label: 'Sincronizador FoxPro / ERP',
    actionTag: 'Subir DBF y Sincronizar ERP',
    scope: 'Sistemas / TI',
    description: 'Habilita la carga de archivos DBF para sincronizar precios, stock y catálogo con el ERP.'
  }
};
