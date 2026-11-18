import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBoxOpen, faArrowRight } from '@fortawesome/free-solid-svg-icons';

import SEO from '../components/common/SEO';
import BRAND from '../config/brand';
import promoAdService from '../services/promoAdService';

import SearchBar from '../components/layout/SearchBar';
import StoriesBar from '../components/announcements/StoriesBar';
import Footer from '../components/layout/Footer';
import LoadingSpinner from '../components/common/LoadingSpinner';
import PromoAdSectionBlock from '../components/promoAds/PromoAdSectionBlock';

/**
 * Página de inicio B2B con publicidad de inicio.
 * Si no existen bloques publicitarios activos, redirige automáticamente al catálogo (/products).
 */
export default function PromoAdsHome() {
  const navigate = useNavigate();
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const loadAds = async () => {
      try {
        const data = await promoAdService.getActiveAds();
        if (!active) return;

        if (!data?.has_ads || !Array.isArray(data.sections) || data.sections.length === 0) {
          navigate('/products', { replace: true });
          return;
        }

        setSections(data.sections);
      } catch (err) {
        console.error('Error al cargar publicidad de inicio:', err);
        if (active) {
          navigate('/products', { replace: true });
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    loadAds();
    return () => {
      active = false;
    };
  }, [navigate]);

  if (loading) {
    return (
      <div className="page-wrapper">
        <SearchBar />
        <main className="main">
          <div className="container">
            <LoadingSpinner message="Cargando novedades y promociones..." />
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="page-wrapper">
      <SEO title={`Novedades y Promociones | ${BRAND.name}`} />
      <SearchBar />

      <main className="main promo-ads">
        <div className="container">
          <StoriesBar />

          <div className="promo-ads__sections">
            {sections.map((section) => (
              <PromoAdSectionBlock key={section.section_id} section={section} />
            ))}
          </div>

          <div className="promo-ads__cta">
            <button
              type="button"
              className="btn btn--primary btn--lg promo-ads__cta-btn"
              onClick={() => navigate('/products')}
            >
              <FontAwesomeIcon icon={faBoxOpen} />
              <span>Ir al Catálogo de Productos</span>
              <FontAwesomeIcon icon={faArrowRight} />
            </button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
