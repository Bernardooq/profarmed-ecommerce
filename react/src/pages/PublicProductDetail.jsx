import { useState, useEffect } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowLeft, faSignInAlt, faUserPlus, faStore } from '@fortawesome/free-solid-svg-icons';

import catalogService from '../services/catalogService';
import BRAND from '../config/brand';
import { getProductImageUrl } from '../utils/imageUtils';
import { formatCurrency } from '../utils/formatUtils';
import { createBreadcrumbSchema, createProductSchema } from '../utils/schemas';

import SEO from '../components/common/SEO';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function PublicProductDetail() {
  const { productId } = useParams();
  const [searchParams] = useSearchParams();
  const listParam = searchParams.get('list');

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const loadProduct = async () => {
      try {
        setLoading(true);
        setNotFound(false);
        const data = await catalogService.getPublicProduct(productId, listParam);
        if (isMounted) {
          if (data && data.product_id) {
            setProduct(data);
          } else {
            setNotFound(true);
          }
        }
      } catch {
        if (isMounted) {
          setProduct(null);
          setNotFound(true);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadProduct();
    return () => {
      isMounted = false;
    };
  }, [productId, listParam]);

  if (loading) {
    return (
      <div className="page">
        <SEO title={BRAND.getTitle('Detalle de Producto')} canonical={BRAND.getCanonical(`/catalogo/producto/${encodeURIComponent(productId || '')}`)} />
        <Header />
        <main className="page__content">
          <div className="page-container">
            <LoadingSpinner message="Cargando información del producto..." />
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (notFound || !product) {
    return (
      <div className="page">
        <SEO
          title={BRAND.getTitle('Producto no disponible')}
          description={`El producto solicitado no está disponible en el catálogo público de ${BRAND.name}.`}
          canonical={BRAND.getCanonical('/catalogo')}
          noindex={true}
        />
        <Header />
        <main className="page__content">
          <div className="page-container">
            <div className="card p-8 text-center max-w-lg mx-auto my-8">
              <h1 className="font-bold text-xl mb-2">Producto no disponible</h1>
              <p className="text-muted mb-4">
                Este producto no forma parte actualmente del catálogo público abierto o requiere iniciar sesión como cliente autorizado.
              </p>
              <div className="d-flex justify-center gap-3 flex-wrap">
                <Link to="/catalogo" className="btn btn--secondary btn--sm">
                  <FontAwesomeIcon icon={faArrowLeft} className="mr-1" />
                  Ir al Catálogo Público
                </Link>
                <Link to="/login" className="btn btn--primary btn--sm">
                  <FontAwesomeIcon icon={faSignInAlt} className="mr-1" />
                  Iniciar Sesión
                </Link>
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const canonicalUrl = BRAND.getCanonical(`/catalogo/producto/${encodeURIComponent(product.product_id)}`);
  const displayPrice = product.final_price !== null && product.final_price !== undefined ? product.final_price : 0;
  const isAvailable = product.stock_count > 0 && product.is_active;
  const productImage = product.image_url ? getProductImageUrl(product) : null;

  const descriptionParts = [
    product.name,
    product.category?.name ? `Categoría: ${product.category.name}` : null,
    product.description,
    product.codebar ? `Código: ${product.codebar}` : null,
    `Precio mayorista de referencia $${Number(displayPrice).toFixed(2)} MXN en ${BRAND.name}.`,
  ].filter(Boolean);

  const seoDescription = descriptionParts.join(' · ').slice(0, 160);

  const breadcrumbSchema = createBreadcrumbSchema([
    { name: 'Inicio', url: `${BRAND.domain}/` },
    { name: 'Catálogo Público', url: `${BRAND.domain}/catalogo` },
    { name: product.name, url: canonicalUrl },
  ]);

  const productSchema = createProductSchema(product, {
    canonicalUrl,
    priceListName: product.price_list_name,
  });

  return (
    <div className="page">
      <SEO
        title={BRAND.getTitle(product.name)}
        description={seoDescription}
        keywords={[product.name, product.category?.name, product.codebar, BRAND.name, 'mayoreo B2B'].filter(Boolean).join(', ')}
        canonical={canonicalUrl}
        ogType="product"
        ogImage={productImage}
        productMeta={{
          price: Number(displayPrice).toFixed(2),
          availability: isAvailable ? 'in stock' : 'out of stock',
        }}
        schema={[breadcrumbSchema, productSchema]}
      />

      <Header />

      <main className="page__content">
        <div className="page-container">
          <nav aria-label="Breadcrumb" className="mb-4 text-sm text-muted d-flex align-items-center gap-2 flex-wrap">
            <Link to="/" className="text-muted" style={{ textDecoration: 'none' }}>Inicio</Link>
            <span>/</span>
            <Link to="/catalogo" className="text-muted" style={{ textDecoration: 'none' }}>Catálogo Público</Link>
            <span>/</span>
            <span className="font-medium">{product.name}</span>
          </nav>

          <div className="mb-4">
            <Link to="/catalogo" className="btn btn--ghost btn--sm">
              <FontAwesomeIcon icon={faArrowLeft} className="mr-1" />
              Volver al catálogo
            </Link>
          </div>

          <article className="card p-6 shadow-xs">
            <div className="d-flex align-items-center gap-2 mb-3 flex-wrap">
              <span className="badge badge--primary text-xs">
                <FontAwesomeIcon icon={faStore} className="mr-1" />
                Catálogo Público
              </span>
              {product.price_list_name && (
                <span className="badge badge--secondary text-xs">{product.price_list_name}</span>
              )}
              {product.category?.name && (
                <span className="badge badge--secondary text-xs">{product.category.name}</span>
              )}
            </div>

            <h1 className="section-title mb-4">{product.name}</h1>

            <div className="product-details" style={{ marginBottom: 0 }}>
              <div className="product-details__image">
                <img src={getProductImageUrl(product)} alt={product.name} />
              </div>

              <div className="product-details__info">
                <div>
                  <span className="product-details__codebar">
                    Código: {product.codebar || product.product_id}
                  </span>
                </div>

                {product.has_discount && product.original_price && (
                  <div className="product-details__discount-row">
                    <span className="product-details__original-price">
                      {formatCurrency(product.original_price)} MXN
                    </span>
                    <span className="product-details__discount-badge">
                      -{product.discount_applied}%
                    </span>
                    {product.savings > 0 && (
                      <span className="product-details__savings">
                        Ahorras {formatCurrency(product.savings)}
                      </span>
                    )}
                  </div>
                )}

                <div className="product-details__price">
                  {formatCurrency(displayPrice)} MXN
                  <small className="d-block text-muted text-xs font-normal mt-1">Precio de referencia (IVA incluido)</small>
                </div>

                <div className={`stock-badge ${isAvailable ? 'stock-badge--in-stock' : 'stock-badge--out-of-stock'}`}>
                  {isAvailable ? (
                    <span>✓ En stock ({product.stock_count} unidades disponibles)</span>
                  ) : (
                    <span>✗ Producto agotado</span>
                  )}
                </div>

                <div className="product-details__description">
                  <h2>Descripción</h2>
                  {product.unidad_medida && (
                    <p><strong>Unidad de medida:</strong> {product.unidad_medida}</p>
                  )}
                  <p>{product.description || 'Sin descripción disponible'}</p>
                  {product.descripcion_2 && <p>{product.descripcion_2}</p>}
                </div>

                <div className="product-details__actions" style={{ marginTop: '16px' }}>
                  <p className="text-muted text-sm mb-3">
                    Para realizar compras y levantar pedidos mayoristas, inicia sesión o regístrate como cliente B2B.
                  </p>
                  <div className="d-flex gap-2 flex-wrap">
                    <Link to="/quiero-ser-cliente" className="btn btn--primary" style={{ textDecoration: 'none' }}>
                      <FontAwesomeIcon icon={faUserPlus} className="mr-1" />
                      Quiero ser cliente
                    </Link>
                    <Link to="/login" className="btn btn--secondary" style={{ textDecoration: 'none' }}>
                      <FontAwesomeIcon icon={faSignInAlt} className="mr-1" />
                      Iniciar Sesión
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </main>

      <Footer />
    </div>
  );
}

