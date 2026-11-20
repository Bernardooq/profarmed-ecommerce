/**
 * Home.jsx
 * =======
 * Página principal - Plataforma B2B
 * 
 * Esta página muestra el contenido landing con información de la empresa,
 * productos destacados, ventajas y laboratorios asociados.
 * 
 * Funcionalidades:
 * - Renderiza diferentes headers según el rol del usuario (público, cliente, staff)
 * - Muestra secciones: Hero, Intro, Productos Destacados, Ventajas, Laboratorios
 * - Responsive y accesible para todos los usuarios
 */

import { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/layout/Header';
import Header2 from '../components/layout/Header2';
import SearchBar from '../components/layout/SearchBar';
import Footer from '../components/layout/Footer';
import Hero from '../components/hero/Hero';
import Labs from '../components/common/Labs';
import SEO from '../components/common/SEO';
import { organizationSchema, localBusinessSchema, websiteSchema, PHARMA_SEO_KEYWORDS } from '../utils/schemas';
import BRAND from '../config/brand';
import content from '../config/content.json';
import { resolveBrandAsset } from '../utils/brandAssets';

export default function Home() {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  const isStaff = isAuthenticated && user?.role !== 'customer';

  useEffect(() => {
    if (isStaff) {
      navigate('/dashboard', { replace: true });
    }
  }, [isStaff, navigate]);

  if (isStaff) {
    return null;
  }

  const combinedSchema = {
    "@context": "https://schema.org",
    "@graph": [organizationSchema, localBusinessSchema, websiteSchema]
  };

  const inicio = content?.inicio || {};
  const productsBanner = inicio.productsBanner || {};
  const allies = inicio.allies || {};
  const solutions = inicio.solutions || {};
  const trustBar = inicio.trustBar || {};
  const reviews = inicio.reviews || {};
  const ctaBanner = inicio.ctaBanner || {};
  const whatsappUrl = `https://wa.me/${content?.brand?.whatsapp || '523338545849'}`;

  const renderHeader = () => {
    if (!isAuthenticated) return <Header />;
    if (isStaff) return <Header2 />;
    return <SearchBar />;
  };

  return (
    <div className="page">
      <SEO
        title={BRAND.getTitle()}
        description={inicio.intro || BRAND.shortDescription}
        keywords={PHARMA_SEO_KEYWORDS}
        canonical={BRAND.getCanonical('/')}
        ogType="website"
        schema={combinedSchema}
      />

      {renderHeader()}

      <main className="page__content">
        {/* 1. Hero con imagen de fondo por default */}
        <Hero />

        {/* 2. Banner +2,000 productos a tu disposición */}
        <section className="pf-section pf-section--light">
          <div className="pf-section__container">
            <div className="pf-section__header">
              <div className="pf-section__title-wrap">
                <h2 className="pf-section__title">{productsBanner.title}</h2>
                <div className="pf-divider">
                  <span className="pf-divider__primary" />
                  <span className="pf-divider__secondary" />
                </div>
              </div>
              <p className="pf-section__subtitle">{productsBanner.subtitle}</p>
              <div style={{ marginTop: 'var(--space-6)' }}>
                <a
                  href={whatsappUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="pf-pill-btn"
                >
                  {productsBanner.ctaIcon && (
                    <img src={resolveBrandAsset(productsBanner.ctaIcon)} alt="" />
                  )}
                  <span>{productsBanner.ctaText}</span>
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Tus aliados en distribución */}
        <section className="pf-section pf-section--dark-gradient pf-section--allies">
          <div className="pf-section__container">
            <div className="pf-split">
              <div className="pf-split__body">
                <div className="pf-section__header pf-section__header--left">
                  <div className="pf-section__title-wrap">
                    <h2 className="pf-section__title">{allies.title}</h2>
                    <div className="pf-divider pf-divider--left pf-divider--on-dark">
                      <span className="pf-divider__primary" />
                      <span className="pf-divider__secondary" />
                    </div>
                  </div>
                </div>
                <p>{allies.description}</p>
                <p>
                  {allies.highlightPrefix}
                  <span className="pf-split__highlight">{allies.highlightText}</span>
                </p>
                <div style={{ marginTop: 'var(--space-6)' }}>
                  <Link to={allies.ctaLink || '/about'} className="pf-pill-btn pf-pill-btn--dark-text">
                    {allies.ctaText}
                  </Link>
                </div>
              </div>

              <div className="pf-split__media">
                {allies.imageUrl ? (
                  <picture>
                    {allies.mobileImageUrl && (
                      <source media="(max-width: 767px)" srcSet={resolveBrandAsset(allies.mobileImageUrl)} />
                    )}
                    <img src={resolveBrandAsset(allies.imageUrl)} alt={allies.title} loading="lazy" />
                  </picture>
                ) : (
                  <div className="pf-split__pending">
                    Espacio reservado para imagen / SVG de distribución
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* 4. Soluciones para cada necesidad de suministro */}
        <section className="pf-section pf-section--green">
          <div className="pf-section__container">
            <div className="pf-section__header">
              <div className="pf-section__title-wrap">
                <h2 className="pf-section__title">{solutions.title}</h2>
                <div className="pf-divider pf-divider--on-green">
                  <span className="pf-divider__primary" />
                  <span className="pf-divider__secondary" />
                </div>
              </div>
            </div>

            <div className="pf-mountains-grid">
              {(solutions.items || []).map((item, idx) => (
                <div key={idx} className="pf-mountain-card">
                  {item.icon && (
                    <img src={resolveBrandAsset(item.icon)} alt={item.title} className="pf-mountain-card__icon" loading="lazy" />
                  )}
                  <div className="pf-mountain-card__title-wrap">
                    <div className="pf-divider pf-divider--on-green">
                      <span className="pf-divider__primary" />
                      <span className="pf-divider__secondary" />
                    </div>
                    <h3 className="pf-mountain-card__title">{item.title}</h3>
                  </div>
                  {(item.paragraphs || []).map((p, pIdx) => (
                    <p key={pIdx}>{p}</p>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 5. Barra de confianza */}
        <section className="pf-trust-bar">
          <div className="pf-trust-bar__grid">
            {(trustBar.items || []).map((text, idx) => (
              <div key={idx} className="pf-trust-bar__item">
                {trustBar.icon && <img src={resolveBrandAsset(trustBar.icon)} alt="" loading="lazy" />}
                <span>{text}</span>
              </div>
            ))}
          </div>
        </section>

        {/* 6. +150 socios comerciales (Carrusel 2x5) */}
        <Labs />

        {/* 7. +500 clientes satisfechos (Reseñas) */}
        <section className="pf-section pf-section--night">
          <div className="pf-section__container">
            <div className="pf-reviews">
              <div className="pf-reviews__visual">
                {(reviews.items || []).map((rev, idx) => {
                  const avatar = (
                    <div className="pf-reviews__avatar">
                      {rev.avatarUrl && <img src={resolveBrandAsset(rev.avatarUrl)} alt={rev.name} loading="lazy" />}
                    </div>
                  );
                  const badge = (
                    <div className={`pf-reviews__badge ${idx === 1 ? 'pf-reviews__badge--span2' : 'pf-reviews__badge--span3'}`}>
                      <span>{rev.name}</span>
                      <div className="pf-reviews__stars">
                        {'★'.repeat(rev.rating || 5)}
                      </div>
                    </div>
                  );

                  return (
                    <div key={idx} style={{ display: 'contents' }}>
                      {idx === 1 && (
                        <>
                          <span className="pf-reviews__dec-circle" aria-hidden="true" />
                          <span className="pf-reviews__dec-circle" aria-hidden="true" />
                          <span className="pf-reviews__dec-circle" aria-hidden="true" />
                          <span className="pf-reviews__dec-circle" aria-hidden="true" />
                        </>
                      )}
                      {idx === 0 && (
                        <>
                          {avatar}
                          {badge}
                        </>
                      )}
                      {idx === 1 && (
                        <>
                          <span className="pf-reviews__dec-circle" aria-hidden="true" />
                          {avatar}
                          {badge}
                        </>
                      )}
                      {idx >= 2 && (
                        <>
                          {badge}
                          {avatar}
                        </>
                      )}
                    </div>
                  );
                })}
              </div>

              <div>
                <div className="pf-section__header pf-section__header--left">
                  <div className="pf-section__title-wrap">
                    <h2 className="pf-section__title">
                      <span className="pf-reviews__number">{reviews.titleHighlight}</span>
                      {reviews.titleRest}
                    </h2>
                    <div className="pf-divider pf-divider--left pf-divider--on-dark-rev">
                      <span className="pf-divider__primary" />
                      <span className="pf-divider__secondary" />
                    </div>
                  </div>
                  <p className="pf-section__subtitle">
                    {reviews.subtitlePrefix}
                    <span className="pf-split__highlight pf-split__highlight--block">{reviews.subtitleHighlight}</span>
                  </p>
                  <div style={{ marginTop: 'var(--space-6)' }}>
                    {/^https?:\/\//i.test(reviews.ctaLink || '') ? (
                      <a
                        href={reviews.ctaLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="pf-pill-btn pf-pill-btn--dark-text"
                      >
                        {reviews.ctaText}
                      </a>
                    ) : (
                      <Link to={reviews.ctaLink || '/about'} className="pf-pill-btn pf-pill-btn--dark-text">
                        {reviews.ctaText}
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 8. CTA Final: ¿Necesita un proveedor farmacéutico confiable? */}
        <section className="pf-section pf-section--dark-gradient pf-cta-banner">
          {ctaBanner.watermarkUrl && (
            <img
              src={resolveBrandAsset(ctaBanner.watermarkUrl)}
              alt=""
              className="pf-cta-banner__watermark"
              loading="lazy"
            />
          )}
          <div className="pf-section__container">
            <div className="pf-section__header">
              <div className="pf-section__title-wrap">
                <h2 className="pf-section__title">{ctaBanner.title}</h2>
                <div className="pf-divider pf-divider--on-dark-rev">
                  <span className="pf-divider__primary" />
                  <span className="pf-divider__secondary" />
                </div>
              </div>
              <p className="pf-section__subtitle">{ctaBanner.subtitle}</p>
            </div>

            <div className="pf-cta-banner__actions">
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="pf-pill-btn"
              >
                {ctaBanner.whatsappIcon && <img src={resolveBrandAsset(ctaBanner.whatsappIcon)} alt="" />}
                <span>{ctaBanner.whatsappCtaText}</span>
              </a>
              <Link
                to={ctaBanner.clientCtaLink || '/quiero-ser-cliente'}
                className="pf-pill-btn pf-pill-btn--dark-text"
              >
                {ctaBanner.clientCtaText}
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}