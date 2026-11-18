import { Link } from 'react-router-dom';

/**
 * Renderiza una imagen publicitaria responsiva (<picture>) usando las variantes
 * desktop, tablet y móvil con fallback automático si falta alguna resolución.
 */
export default function PromoAdResponsiveImage({ item }) {
  const desktopSrc = item.img_desktop_url || item.img_tablet_url || item.img_mobile_url;
  const tabletSrc = item.img_tablet_url || desktopSrc;
  const mobileSrc = item.img_mobile_url || tabletSrc;

  const pictureNode = (
    <picture className="promo-ads__picture">
      {mobileSrc && <source media="(max-width: 767px)" srcSet={mobileSrc} />}
      {tabletSrc && <source media="(max-width: 1023px)" srcSet={tabletSrc} />}
      <img
        src={desktopSrc}
        alt={item.title || 'Publicidad promocional'}
        className="promo-ads__img"
        loading="lazy"
      />
    </picture>
  );

  if (!item.link_url) {
    return <div className="promo-ads__media">{pictureNode}</div>;
  }

  const isExternal = /^https?:\/\//i.test(item.link_url);
  if (isExternal) {
    return (
      <a
        href={item.link_url}
        target="_blank"
        rel="noopener noreferrer"
        className="promo-ads__media promo-ads__media--clickable"
        aria-label={item.title || 'Ver promoción'}
      >
        {pictureNode}
      </a>
    );
  }

  return (
    <Link
      to={item.link_url}
      className="promo-ads__media promo-ads__media--clickable"
      aria-label={item.title || 'Ver promoción'}
    >
      {pictureNode}
    </Link>
  );
}
