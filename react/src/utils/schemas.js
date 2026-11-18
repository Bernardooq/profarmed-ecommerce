/**
 * schemas.js
 * ==========
 * Schema.org JSON-LD estructurados para SEO & Google Rich Results.
 * Dinámicos según la configuración de BRAND (White-Label).
 */

import BRAND from '../config/brand';

const DEFAULT_LOGO_URL = `${BRAND.domain}${BRAND.logoUrl || '/pwa-icons/icon-512x512.png'}`;

function resolvePublicProductImage(product) {
  const raw = product?.image_url;
  if (raw && /^https?:\/\//i.test(raw)) {
    const version = product.image_version || 1;
    const sep = raw.includes('?') ? '&' : '?';
    return `${raw}${sep}v=${version}`;
  }
  return DEFAULT_LOGO_URL;
}

// Schema de la Organización (usar en Home y About)
export const organizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: BRAND.name,
  legalName: BRAND.legalName,
  url: BRAND.domain,
  logo: DEFAULT_LOGO_URL,
  description: BRAND.shortDescription,
  email: BRAND.contactEmail,
  address: {
    '@type': 'PostalAddress',
    addressCountry: 'MX',
  },
  contactPoint: {
    '@type': 'ContactPoint',
    telephone: BRAND.phone ? `+52-${BRAND.phone}` : undefined,
    email: BRAND.contactEmail,
    contactType: 'customer service',
    areaServed: 'MX',
    availableLanguage: ['Spanish'],
  },
};

// Schema de Breadcrumbs (usar en páginas internas y catálogo)
export const createBreadcrumbSchema = (items) => ({
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: items.map((item, index) => ({
    '@type': 'ListItem',
    position: index + 1,
    name: item.name,
    item: item.url,
  })),
});

// Schema de WebSite (usar en Home) con buscador dirigido al catálogo público indexable
export const websiteSchema = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: BRAND.name,
  url: BRAND.domain,
  description: `${BRAND.name} - ${BRAND.shortDescription}`,
  publisher: {
    '@type': 'Organization',
    name: BRAND.name,
  },
  potentialAction: {
    '@type': 'SearchAction',
    target: `${BRAND.domain}/catalogo?search={search_term_string}`,
    'query-input': 'required name=search_term_string',
  },
};

// Schema de LocalBusiness (usar en Contact)
export const localBusinessSchema = {
  '@context': 'https://schema.org',
  '@type': 'WholesaleStore',
  name: BRAND.name,
  image: DEFAULT_LOGO_URL,
  '@id': BRAND.domain,
  url: BRAND.domain,
  email: BRAND.contactEmail,
  telephone: BRAND.phone ? `+52-${BRAND.phone}` : undefined,
  priceRange: '$$',
  address: {
    '@type': 'PostalAddress',
    addressCountry: 'MX',
  },
  areaServed: {
    '@type': 'Country',
    name: 'MX',
  },
};

// Schema de Producto individual para Google Rich Results (/catalogo/producto/:productId)
export const createProductSchema = (product, { canonicalUrl, priceListName } = {}) => {
  if (!product) return null;

  const productUrl = canonicalUrl || `${BRAND.domain}/catalogo/producto/${encodeURIComponent(product.product_id)}`;
  const rawPrice = product.final_price ?? 0;
  const numericPrice = Number(rawPrice);
  const isAvailable = Number(product.stock_count) > 0 && product.is_active !== false;
  const cleanCodebar = String(product.codebar || '').trim();
  const isValidGtin = /^\d{8}$|^\d{12,14}$/.test(cleanCodebar);

  const descriptionParts = [
    product.description,
    product.descripcion_2,
    product.unidad_medida ? `Presentación: ${product.unidad_medida}` : null,
    priceListName ? `Lista: ${priceListName}` : null,
  ].filter(Boolean);

  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    sku: String(product.product_id),
    mpn: cleanCodebar || String(product.product_id),
    ...(isValidGtin ? { gtin: cleanCodebar } : {}),
    description: descriptionParts.join(' — ') || `${product.name} disponible en el catálogo B2B de ${BRAND.name}.`,
    image: [resolvePublicProductImage(product)],
    ...(product.category?.name ? { category: product.category.name } : {}),
    brand: {
      '@type': 'Brand',
      name: BRAND.name,
    },
    offers: {
      '@type': 'Offer',
      url: productUrl,
      priceCurrency: 'MXN',
      price: Number.isFinite(numericPrice) ? numericPrice.toFixed(2) : '0.00',
      availability: isAvailable ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
      itemCondition: 'https://schema.org/NewCondition',
      seller: {
        '@type': 'Organization',
        name: BRAND.legalName || BRAND.name,
      },
    },
  };
};

// Schema ItemList / CollectionPage para el catálogo público
export const createCatalogItemListSchema = (
  products = [],
  { catalogUrl = `${BRAND.domain}/catalogo`, name = `Catálogo Público - ${BRAND.name}`, description = BRAND.shortDescription } = {}
) => {
  if (!Array.isArray(products) || products.length === 0) {
    return null;
  }

  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name,
    description,
    url: catalogUrl,
    mainEntity: {
      '@type': 'ItemList',
      numberOfItems: products.length,
      itemListElement: products.map((product, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        url: `${BRAND.domain}/catalogo/producto/${encodeURIComponent(product.product_id)}`,
        name: product.name,
      })),
    },
  };
};
