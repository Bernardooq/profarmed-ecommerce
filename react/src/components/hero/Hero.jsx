import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import content from '../../config/content.json';

export default function Hero() {
  const { isAuthenticated } = useAuth();
  const { hero } = content.inicio;
  const ctaText = hero.ctaText || 'Ir al e-commerce';
  const targetRoute = isAuthenticated ? '/products' : '/login';

  return (
    <section className="hero">
      <div className="hero__bg-image hero__bg-image--inicio"></div>
      {(hero.title || hero.subtitle) && (
        <div className="hero__content">
          {hero.title && (
            <h1 className="hero__title">
              {hero.title}
              {hero.srOnly && <span className="sr-only">{hero.srOnly}</span>}
            </h1>
          )}
          {hero.subtitle && <h2 className="hero__subtitle">{hero.subtitle}</h2>}
        </div>
      )}
      {ctaText && (
        <div className="hero__cta-wrap">
          <Link to={targetRoute} className="pf-pill-btn pf-pill-btn--dark-text">
            {ctaText}
          </Link>
        </div>
      )}
    </section>
  );
}