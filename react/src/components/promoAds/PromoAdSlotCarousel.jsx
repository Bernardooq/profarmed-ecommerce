import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChevronLeft, faChevronRight } from '@fortawesome/free-solid-svg-icons';
import PromoAdResponsiveImage from './PromoAdResponsiveImage';

/**
 * Renderiza una columna (slot) dentro de una sección publicitaria.
 * Si hay 1 anuncio lo muestra estático; si hay 2 o más habilita carrusel automático.
 */
export default function PromoAdSlotCarousel({ items = [], autoPlayMs = 5000 }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const count = items.length;

  useEffect(() => {
    if (activeIndex >= count && count > 0) {
      setActiveIndex(0);
    }
  }, [count, activeIndex]);

  useEffect(() => {
    if (count <= 1 || isPaused) return undefined;
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % count);
    }, autoPlayMs);
    return () => clearInterval(timer);
  }, [count, isPaused, autoPlayMs]);

  if (count === 0) {
    return null;
  }

  const handlePrev = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveIndex((prev) => (prev - 1 + count) % count);
  };

  const handleNext = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveIndex((prev) => (prev + 1) % count);
  };

  return (
    <div
      className="promo-ads__slot"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="promo-ads__carousel">
        <div
          className="promo-ads__track"
          style={{ transform: `translateX(-${activeIndex * 100}%)` }}
        >
          {items.map((item) => (
            <div key={item.item_id} className="promo-ads__slide">
              <PromoAdResponsiveImage item={item} />
            </div>
          ))}
        </div>

        {count > 1 && (
          <>
            <button
              type="button"
              className="promo-ads__arrow promo-ads__arrow--prev"
              onClick={handlePrev}
              aria-label="Anuncio anterior"
            >
              <FontAwesomeIcon icon={faChevronLeft} />
            </button>
            <button
              type="button"
              className="promo-ads__arrow promo-ads__arrow--next"
              onClick={handleNext}
              aria-label="Siguiente anuncio"
            >
              <FontAwesomeIcon icon={faChevronRight} />
            </button>

            <div className="promo-ads__dots" role="tablist" aria-label="Indicadores de anuncios">
              {items.map((item, idx) => (
                <button
                  key={item.item_id}
                  type="button"
                  role="tab"
                  aria-selected={idx === activeIndex}
                  aria-label={`Ir al anuncio ${idx + 1}`}
                  className={`promo-ads__dot ${idx === activeIndex ? 'promo-ads__dot--active' : ''}`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setActiveIndex(idx);
                  }}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
