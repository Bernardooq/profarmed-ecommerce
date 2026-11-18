/**
 * SEO.jsx
 * =======
 * Componente reutilizable para gestionar meta tags SEO, Open Graph,
 * Twitter Cards, directivas robots y datos estructurados Schema.org (JSON-LD).
 */

import { Helmet } from 'react-helmet-async';
import BRAND from '../../config/brand';

const DEFAULT_ROBOTS = 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1';

function toAbsoluteUrl(urlOrPath) {
  const baseDomain = (BRAND.domain || '').replace(/\/+$/, '');
  if (!urlOrPath) {
    const fallbackPath = BRAND.logoUrl || '/pwa-icons/icon-512x512.png';
    return fallbackPath.startsWith('http') ? fallbackPath : `${baseDomain}${fallbackPath.startsWith('/') ? '' : '/'}${fallbackPath}`;
  }
  if (/^https?:\/\//i.test(urlOrPath)) {
    return urlOrPath;
  }
  return `${baseDomain}${urlOrPath.startsWith('/') ? '' : '/'}${urlOrPath}`;
}

function normalizeSchema(schema) {
  if (!schema) return null;
  if (Array.isArray(schema)) {
    const validItems = schema.filter(Boolean);
    if (validItems.length === 0) return null;
    if (validItems.length === 1) return validItems[0];
    return {
      '@context': 'https://schema.org',
      '@graph': validItems.map((item) => {
        if (item && typeof item === 'object' && '@context' in item) {
          const { '@context': _ctx, ...rest } = item;
          return rest;
        }
        return item;
      }),
    };
  }
  return schema;
}

export default function SEO({
  title = BRAND.getTitle(),
  description = BRAND.shortDescription,
  keywords = null,
  canonical = BRAND.domain,
  ogType = 'website',
  ogImage = null,
  schema = null,
  noindex = false,
  robots = null,
  productMeta = null,
}) {
  const resolvedImage = toAbsoluteUrl(ogImage);
  const robotsContent = noindex ? 'noindex, nofollow, noarchive' : (robots || DEFAULT_ROBOTS);
  const normalizedSchema = normalizeSchema(schema);

  return (
    <Helmet>
      <html lang="es" />
      <title>{title}</title>
      <meta name="description" content={description} />
      {keywords && <meta name="keywords" content={keywords} />}
      <meta name="robots" content={robotsContent} />
      <meta name="googlebot" content={robotsContent} />

      {/* Canonical & Hreflang */}
      {canonical && <link rel="canonical" href={canonical} />}
      {!noindex && canonical && <link rel="alternate" hrefLang="es-MX" href={canonical} />}

      {/* Open Graph / Facebook / WhatsApp */}
      <meta property="og:type" content={ogType} />
      <meta property="og:locale" content="es_MX" />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      {canonical && <meta property="og:url" content={canonical} />}
      <meta property="og:site_name" content={BRAND.name} />
      <meta property="og:image" content={resolvedImage} />
      <meta property="og:image:alt" content={title} />

      {/* Product OpenGraph extras */}
      {productMeta?.price !== undefined && productMeta?.price !== null && (
        <meta property="product:price:amount" content={String(productMeta.price)} />
      )}
      {productMeta?.price !== undefined && productMeta?.price !== null && (
        <meta property="product:price:currency" content="MXN" />
      )}
      {productMeta?.availability && (
        <meta property="product:availability" content={productMeta.availability} />
      )}

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content={`@${BRAND.slug}`} />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={resolvedImage} />

      {/* Schema.org JSON-LD */}
      {normalizedSchema && (
        <script type="application/ld+json">
          {JSON.stringify(normalizedSchema)}
        </script>
      )}
    </Helmet>
  );
}
