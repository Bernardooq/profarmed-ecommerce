import content from './content.json';

const brandContent = content?.brand || {};

export const BRAND = {
  // Identidad
  name: import.meta.env.VITE_BRAND_NAME || brandContent.name || 'Comercio B2B',
  legalName: brandContent.legalName || brandContent.name || 'Comercio B2B S.A. de C.V.',
  shortDescription: brandContent.shortDescription || 'Plataforma B2B de comercio electrónico y distribución.',
  slogan: brandContent.slogan || '',
  domain: brandContent.domain || 'https://ejemplo.com',
  contactEmail: brandContent.contactEmail || 'contacto@ejemplo.com',
  supportEmail: brandContent.supportEmail || brandContent.contactEmail || 'soporte@ejemplo.com',
  phone: brandContent.phone || '',
  whatsapp: brandContent.whatsapp || '',
  slug: brandContent.slug || 'comercio',
  themeColor: (typeof __BRAND_THEME_COLOR__ !== 'undefined' && __BRAND_THEME_COLOR__) ? __BRAND_THEME_COLOR__ : (brandContent.themeColor || '#10b981'),
  logoText: brandContent.logoText || brandContent.name || 'Comercio B2B',
  logoUrl: brandContent.logoUrl || '',

  // API Base URL (lee de .env con fallback a content.json)
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || brandContent.apiBaseUrl || 'http://localhost:8000',

  // Seguridad / Turnstile (lee de .env con fallback a content.json)
  turnstileSiteKey: import.meta.env.VITE_TURNSTILE_SITE_KEY || brandContent.turnstileSiteKey || '',

  // Helpers de SEO y URLs
  getTitle: (pageTitle) => {
    if (!pageTitle) return `${BRAND.name} - Plataforma B2B de Comercio Electrónico`;
    return `${pageTitle} | ${BRAND.name}`;
  },

  getCanonical: (path = '') => {
    const cleanPath = path ? (path.startsWith('/') ? path : `/${path}`) : '';
    return `${BRAND.domain}${cleanPath}`;
  }
};

export default BRAND;
