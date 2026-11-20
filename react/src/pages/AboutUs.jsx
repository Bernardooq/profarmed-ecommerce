/**
 * AboutUs.jsx
 * ===========
 * Página "Acerca de Nosotros" - Plataforma B2B
 * 
 * Contenido:
 * - Hero section con introducción
 * - Historia de la empresa
 * - Misión, Visión y Valores
 * - Estadísticas de la empresa
 * - Razones para elegir la plataforma
 * - Call-to-action para contacto
 * 
 * Acceso: Página pública (no requiere autenticación)
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/layout/Header';
import Header2 from '../components/layout/Header2';
import SearchBar from '../components/layout/SearchBar';
import Footer from '../components/layout/Footer';
import SEO from '../components/common/SEO';
import { organizationSchema, createBreadcrumbSchema } from '../utils/schemas';
import content from '../config/content.json';
import BRAND from '../config/brand';
import { resolveBrandAsset } from '../utils/brandAssets';

export default function AboutUs() {
  const { isAuthenticated, user } = useAuth();
  const [activeTab, setActiveTab] = useState('mission');

  const breadcrumbSchema = createBreadcrumbSchema([
    { name: 'Inicio', url: `${BRAND.domain}/` },
    { name: 'Quienes somos', url: `${BRAND.domain}/about` }
  ]);

  const combinedSchema = {
    "@context": "https://schema.org",
    "@graph": [organizationSchema, breadcrumbSchema]
  };

  const renderHeader = () => {
    if (!isAuthenticated) return <Header />;
    if (user?.role !== 'customer') return <Header2 />;
    return <SearchBar />;
  };

  const nosotros = content.nosotros || {};
  const { hero, introBanner, missionVision, valuesSection, whyChooseUs, ctaBanner } = nosotros;
  const mission = missionVision?.mission || {};
  const vision = missionVision?.vision || {};

  return (
    <div className="page">
      <SEO
        title={BRAND.getTitle('Quienes somos')}
        description={introBanner?.subtitle || BRAND.shortDescription}
        canonical={BRAND.getCanonical('/about')}
        ogType="website"
        schema={combinedSchema}
      />

      {renderHeader()}

      <main className="page__content">
        {/* 1. Hero con imagen */}
        <section className="hero">
          <div className="hero__bg-image hero__bg-image--nosotros" />
          {(hero?.title || hero?.subtitle) && (
            <div className="hero__content">
              {hero?.title && <h1 className="hero__title">{hero.title}</h1>}
              {hero?.subtitle && <p className="hero__subtitle">{hero.subtitle}</p>}
            </div>
          )}
        </section>

        {/* 2. Intro: Proveedora farmacéutica médica */}
        <section className="pf-section pf-section--light">
          <div className="pf-section__container">
            <div className="pf-section__header">
              <div className="pf-section__title-wrap">
                <h2 className="pf-section__title">{introBanner?.title}</h2>
                <div className="pf-divider">
                  <span className="pf-divider__primary" />
                  <span className="pf-divider__secondary" />
                </div>
              </div>
              <p className="pf-section__subtitle">{introBanner?.subtitle}</p>
            </div>
          </div>
        </section>

        {/* 3. Nuestra misión / Nuestra visión (Toggle interactivo) */}
        <section className="pf-section pf-section--dark-gradient pf-section--flush-split">
          <div className="pf-split pf-split--flush">
            <div className="pf-split__body pf-split__body--padded">
              <div className="pf-section__header pf-section__header--left">
                <div className="pf-section__title-wrap">
                  <h2 className="pf-section__title">
                    {activeTab === 'mission' ? mission.title : vision.title}
                  </h2>
                  <div className="pf-divider pf-divider--left pf-divider--on-dark">
                    <span className="pf-divider__primary" />
                    <span className="pf-divider__secondary" />
                  </div>
                </div>
              </div>

              {activeTab === 'mission' ? (
                <p>
                  {mission.prefix}
                  <strong>{mission.boldText}</strong>
                  {mission.middle}
                  <span className="pf-split__highlight">{mission.highlightText}</span>
                  {mission.suffix}
                </p>
              ) : (
                <p>{vision.text}</p>
              )}

              <div className="pf-toggle-pills">
                <button
                  type="button"
                  className={`pf-toggle-pills__btn${activeTab === 'mission' ? ' pf-toggle-pills__btn--active' : ''}`}
                  onClick={() => setActiveTab('mission')}
                >
                  {mission.buttonLabel || 'Misión'}
                </button>
                <button
                  type="button"
                  className={`pf-toggle-pills__btn${activeTab === 'vision' ? ' pf-toggle-pills__btn--active' : ''}`}
                  onClick={() => setActiveTab('vision')}
                >
                  {vision.buttonLabel || 'Visión'}
                </button>
              </div>
            </div>

            <div className="pf-split__media pf-split__media--flush">
              {missionVision?.imageUrl ? (
                <picture>
                  {missionVision?.mobileImageUrl && (
                    <source media="(max-width: 767px)" srcSet={resolveBrandAsset(missionVision.mobileImageUrl)} />
                  )}
                  <img
                    src={resolveBrandAsset(missionVision.imageUrl)}
                    alt={activeTab === 'mission' ? mission.title : vision.title}
                    loading="lazy"
                  />
                </picture>
              ) : (
                <div className="pf-split__pending">
                  Espacio reservado para imagen de Misión / Visión
                </div>
              )}
            </div>
          </div>
        </section>

        {/* 4. Banner Nuestros valores (Degradado 3) + 3 Montañitas */}
        <section className="pf-section pf-section--green-to-navy">
          <div className="pf-section__container">
            <div className="pf-section__header" style={{ marginBottom: 0 }}>
              <div className="pf-section__title-wrap">
                <h2 className="pf-section__title">{valuesSection?.title}</h2>
                <div className="pf-divider pf-divider--on-dark-rev">
                  <span className="pf-divider__primary" />
                  <span className="pf-divider__secondary" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="pf-section pf-section--light">
          <div className="pf-section__container">
            <div className="pf-mountains-grid" style={{ marginTop: 0 }}>
              {(valuesSection?.items || []).map((val, idx) => (
                <div key={idx} className="pf-mountain-card pf-mountain-card--split">
                  <div className="pf-mountain-card__photo">
                    {val.imageUrl ? (
                      <img src={resolveBrandAsset(val.imageUrl)} alt={val.title} loading="lazy" />
                    ) : (
                      <span className="pf-mountain-card__photo-pending">
                        Imagen pendiente ({val.title})
                      </span>
                    )}
                  </div>
                  <div className="pf-mountain-card__body">
                    <h3 className="pf-mountain-card__title">{val.title}</h3>
                    <p>{val.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 5. ¿Por qué escogernos? */}
        <section className="pf-section pf-section--night pf-section--flush-pills">
          <div className="pf-split pf-split--flush-pills">
            <div className="pf-split__body pf-split__body--pills-left">
              <div className="pf-section__header pf-section__header--left">
                <div className="pf-section__title-wrap">
                  <h2 className="pf-section__title">
                    {whyChooseUs?.titlePrefix}
                    <span className="pf-split__highlight">{whyChooseUs?.titleHighlight}</span>
                  </h2>
                  <div className="pf-divider pf-divider--left pf-divider--on-dark-rev">
                    <span className="pf-divider__primary" />
                    <span className="pf-divider__secondary" />
                  </div>
                </div>
              </div>
              <p>{whyChooseUs?.subtitle}</p>
            </div>

            <div className="pf-feature-pills">
              {(whyChooseUs?.items || []).map((item, idx) => (
                <div key={idx} className="pf-feature-pill">
                  <div className="pf-feature-pill__circle">
                    {item.icon && <img src={item.icon} alt={item.title} loading="lazy" />}
                  </div>
                  <div className="pf-feature-pill__content">
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 6. CTA Final: ¿Quiere ser un aliado farmacéutico? */}
        <section className="pf-section pf-section--dark-gradient pf-cta-banner">
          {ctaBanner?.watermarkUrl && (
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
                <h2 className="pf-section__title">{ctaBanner?.title}</h2>
                <div className="pf-divider pf-divider--on-dark-rev">
                  <span className="pf-divider__primary" />
                  <span className="pf-divider__secondary" />
                </div>
              </div>
              <p className="pf-section__subtitle">{ctaBanner?.subtitle}</p>
            </div>

            <div className="pf-cta-banner__actions">
              <Link
                to={ctaBanner?.buttonLink || '/quiero-ser-cliente'}
                className="pf-pill-btn pf-pill-btn--dark-text"
              >
                {ctaBanner?.buttonText}
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
