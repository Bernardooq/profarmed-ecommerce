import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import BRAND from '../../config/brand';
import content from '../../config/content.json';
import catalogService from '../../services/catalogService';
import { resolveBrandAsset } from '../../utils/brandAssets';

export default function Footer() {
  const [hasPublicCatalog, setHasPublicCatalog] = useState(false);
  const footerData = content.footer || {};
  const brandData = content.brand || {};

  useEffect(() => {
    let isMounted = true;
    catalogService.getPublicPriceLists()
      .then((lists) => {
        if (isMounted) {
          setHasPublicCatalog(Array.isArray(lists) && lists.length > 0);
        }
      })
      .catch(() => {
        if (isMounted) setHasPublicCatalog(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <footer className="footer">
      <div className="footer__inner">
        <div className="footer__brand">
          <Link to="/" className="footer__logo">
            {BRAND.logoUrl ? (
              <img src={BRAND.logoUrl} alt={BRAND.name} />
            ) : (
              <span>{BRAND.logoText}</span>
            )}
          </Link>
          <p className="footer__desc">
            {footerData.description || brandData.shortDescription}
          </p>
          <p className="footer__social-title">
            {footerData.socialTitle || 'Síguenos en nuestras redes sociales'}
          </p>
          <div className="footer__socials">
            <a
              href={brandData.social?.instagram || '#'}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Instagram"
            >
              <img src={resolveBrandAsset('icon-instagram.webp')} alt="Instagram" />
            </a>
            <a
              href={brandData.social?.facebook || '#'}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Facebook"
            >
              <img src={resolveBrandAsset('icon-facebook.webp')} alt="Facebook" />
            </a>
          </div>
        </div>

        <div className="footer__section">
          <h4>{footerData.navTitle || 'NAVEGACIÓN'}</h4>
          {(footerData.links || []).map((item) => (
            <Link key={item.to} to={item.to}>{item.label}</Link>
          ))}
          {hasPublicCatalog && <Link to="/catalogo">Catálogo Público</Link>}
        </div>

        <div className="footer__section">
          <h4>{footerData.contactTitle || 'CONTACTO'}</h4>
          <a href={`mailto:${brandData.contactEmail}`} className="footer__contact-link">
            {brandData.contactEmail}
          </a>
          <a href={`tel:${brandData.phone?.replace(/\s+/g, '')}`}>
            {brandData.phone}
          </a>
          {brandData.address && <p>{brandData.address}</p>}
        </div>
      </div>

      <div className="footer__bottom">
        <span>&copy; {new Date().getFullYear()} {BRAND.name}. Todos los derechos reservados.</span>
        <div className="footer__legal">
          <Link to="/terms">Términos y Condiciones</Link>
          <Link to="/privacy">Aviso de Privacidad</Link>
        </div>
      </div>
    </footer>
  );
}
