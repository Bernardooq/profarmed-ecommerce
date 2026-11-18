import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowLeft, faArrowRight } from '@fortawesome/free-solid-svg-icons';
import content from '../../config/content.json';

// Importa todas las imagenes de laboratorios desde la carpeta especificada
const modules = import.meta.glob('../../images/labs/*.webp', { eager: true });

/**
 * Convierte los modulos importados en un array de objetos
 * con id y src para cada logo de laboratorio
 */
const labImages = Object.keys(modules).map((path, index) => {
  const src = modules[path].default || modules[path].src;
  return { id: index + 1, src };
});

const PAGE_SIZE = 10;

export default function Labs() {
  const [selectedLab, setSelectedLab] = useState(null);
  const [page, setPage] = useState(0);
  const labsContent = content.inicio?.labs || {};
  const totalPages = Math.max(1, Math.ceil(labImages.length / PAGE_SIZE));

  const visibleLabs = labImages.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const handlePrev = () => setPage((prev) => (prev - 1 + totalPages) % totalPages);
  const handleNext = () => setPage((prev) => (prev + 1) % totalPages);

  return (
    <section className="pf-section pf-section--light">
      <div className="pf-section__container">
        <div className="pf-section__header">
          <h2 className="pf-section__title">{labsContent.title}</h2>
          <div className="pf-divider">
            <span className="pf-divider__primary" />
            <span className="pf-divider__secondary" />
          </div>
          {labsContent.subtitle && (
            <p className="pf-section__subtitle">{labsContent.subtitle}</p>
          )}
        </div>

        <div className="pf-labs-carousel">
          {totalPages > 1 && (
            <button
              type="button"
              className="pf-labs-carousel__arrow"
              onClick={handlePrev}
              aria-label="Laboratorios anteriores"
            >
              <FontAwesomeIcon icon={faArrowLeft} />
            </button>
          )}

          <div className="pf-labs-carousel__grid">
            {visibleLabs.map((lab) => (
              <div
                key={lab.id}
                className="pf-labs-carousel__item"
                onClick={() => setSelectedLab(lab)}
              >
                <img
                  src={lab.src}
                  alt={`Laboratorio ${lab.id}`}
                  loading="lazy"
                />
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <button
              type="button"
              className="pf-labs-carousel__arrow"
              onClick={handleNext}
              aria-label="Siguientes laboratorios"
            >
              <FontAwesomeIcon icon={faArrowRight} />
            </button>
          )}
        </div>
      </div>

      {/* Modal / Lightbox para ampliar el logo */}
      {selectedLab && (
        <div className="lab-modal-overlay" onClick={() => setSelectedLab(null)}>
          <div className="lab-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="lab-modal-close" onClick={() => setSelectedLab(null)}>&times;</button>
            <div className="lab-modal-image-container">
              <img src={selectedLab.src} alt="Laboratorio ampliado" />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}