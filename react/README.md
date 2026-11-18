# Profarmed — Frontend Web Application (React 19 + PWA)

Cliente web Single Page Application (SPA) para la plataforma B2B de **Profarmed**, optimizada para dispositivos móviles y de escritorio, con soporte Progressive Web App (PWA) e integración con el backend FastAPI.

---

## 🎨 Sistema de Diseño y Tokens SCSS

El diseño visual está completamente estructurado bajo una arquitectura de diseño atómico (*Atomic Design*) con tokens CSS/SCSS parametrizados:

```
react/src/styles/
├── tokens/               # Variables raíz de la identidad de marca
│   ├── _colors.scss      # Paleta de color (Primario: #4F46E5 (Royal Indigo), modo oscuro)
│   ├── _typography.scss  # Familia tipográfica (Plus Jakarta Sans), escalas y pesos
│   ├── _spacing.scss     # Escala de espaciados modulares (rem/px)
│   ├── _breakpoints.scss # Media queries responsivas (mobile, tablet, desktop, wide)
│   └── _shadows.scss     # Elevaciones y sombras de componentes
├── atoms/                # Componentes indivisibles (botones, inputs, badges, spinners)
├── molecules/            # Combinaciones de átomos (tarjetas de producto, grupos de filtro)
├── organisms/            # Secciones completas (Header, Footer, Navbar, Data Tables)
├── templates/            # Diseños de página y layouts (DashboardLayout, StorefrontLayout)
└── main.scss             # Hoja de estilos maestra compilada
```

---

## 🗂️ Estructura del Código Fuente

```
react/src/
├── api/                  # Clientes HTTP axios/fetch configurados con interceptores
├── components/           # Componentes organizados por dominio
│   ├── admin/            # Paneles de administración (clientes, grupos, métricas)
│   ├── announcements/    # Banners de promociones (StoriesBar, PopupBanner, FooterBanner)
│   ├── common/           # Componentes utilitarios (Paginación, SEO, Alertas, PWA Prompt)
│   ├── layout/           # Encabezados, pies de página, drawers y barras de búsqueda
│   ├── modals/           # Ventanas modales de edición, carga de imágenes y confirmaciones
│   ├── orders/           # Tablas y detalles de órdenes de compra
│   ├── products/         # Visualización de catálogo, tarjetas, filtros dinámicos
│   └── users/            # Formularios de login, perfil y cambio de contraseña
├── config/               # Configuración centralizada (api.js, content.json)
├── context/              # Contextos de React para estado global
│   ├── AuthContext.jsx   # Sesión activa, token JWT, rol de usuario y persistencia
│   ├── CartContext.jsx   # Carrito de compras, cantidades y cotización en tiempo real
│   └── PaginationLimitContext.jsx # Preferencias de visualización por página
├── hooks/                # Custom hooks (useCatalogSettings, useSidebar, useTheme)
├── pages/                # Vistas de rutas principales (Home, Products, Cart, Dashboards)
├── routes/               # Configuración de React Router y ProtectedRoute con RBAC
└── services/             # Servicios desacoplados de consumo de API REST
```

---

## 🛡️ Seguridad y Autenticación en el Frontend

- **Interceptores de Peticiones**: Todas las llamadas authenticated inyectan automáticamente el encabezado `Authorization: Bearer <token>` gestionado por `AuthContext`.
- **Protección de Rutas (`ProtectedRoute.jsx`)**: Valida el rol del usuario antes de permitir la navegación a `/admindash`, `/sellerdash` o `/marketingdash`.
- **Sanitización y Validación**: Formularios validados contra inyecciones y tipos estrictos antes del envío.
- **PWA Seguro**: Service Worker registrado para funcionamiento offline (`offline.html`) y control estricto de caché para evitar servir versiones desactualizadas del HTML.

---

## 🛠️ Comandos de Desarrollo

```bash
# Instalar dependencias
npm install --legacy-peer-deps

# Iniciar servidor de desarrollo en http://localhost:5173 (o 3000 con Docker)
npm run dev

# Compilar para producción (comprobación estricta de tipos y bundling Vite)
npm run build

# Previsualizar el build de producción localmente
npm run preview
```
