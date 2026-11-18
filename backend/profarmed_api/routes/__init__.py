"""
Routes Package - PROFARMED API

Este paquete contiene todos los routers de endpoints de la API.

La estructura esta organizada por dominio:
- auth: Autenticacion y sesion
- users: Perfil de usuario
- admin: Administracion de usuarios internos
- customers: CRUD de clientes
- products: CRUD de productos
- categories: CRUD de categorias
- catalog: Catalogo con precios para clientes
- orders: Gestion de pedidos y carrito
- dashboards: Reportes y estadisticas
- commercial_groups: Grupos comerciales N:M
- sync_batch: Sincronizacion por lotes REST
- sync_upload: Sincronizacion asincrona GZIP
- price_lists: Listas de precios
- contact: Formularios de contacto

El router principal se encuentra en router.py
"""

# Este archivo sirve como marcador de paquete Python
# Los routers se importan en router.py
