import React, { useState, useEffect, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTimes, faChevronLeft, faChevronRight, faTag } from '@fortawesome/free-solid-svg-icons';

export default function StoryViewerModal({
  story,
  stories = [],
  onClose,
  duration = 6000
}) {
  const storiesList = stories.length > 0 ? stories : (story ? [story] : []);
  
  const initialIndex = storiesList.findIndex(s => s.id === story?.id);
  const [currentIndex, setCurrentIndex] = useState(initialIndex >= 0 ? initialIndex : 0);
  const [progress, setProgress] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const currentStory = storiesList[currentIndex] || story;

  // Next story handler
  const handleNext = useCallback(() => {
    if (currentIndex < storiesList.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setProgress(0);
    } else {
      onClose();
    }
  }, [currentIndex, storiesList.length, onClose]);

  // Prev story handler
  const handlePrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      setProgress(0);
    } else {
      setProgress(0);
    }
  }, [currentIndex]);

  // Escape key and keyboard arrows listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') handleNext();
      if (e.key === 'ArrowLeft') handlePrev();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, handleNext, handlePrev]);

  // Timer & progress interval (runs every 50ms)
  useEffect(() => {
    if (isPaused || !currentStory) return;

    const stepMs = 50;
    const increment = (stepMs / duration) * 100;

    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev + increment >= 100) {
          handleNext();
          return 0;
        }
        return prev + increment;
      });
    }, stepMs);

    return () => clearInterval(interval);
  }, [isPaused, duration, handleNext, currentStory]);

  if (!currentStory) return null;

  const handleCardClick = (e) => {
    // Si da clic en la parte izquierda (35%), va al anterior. En la derecha (65%), avanza.
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;

    if (clickX < width * 0.35) {
      handlePrev();
    } else {
      handleNext();
    }
  };

  return (
    <div className="story-viewer-overlay" onClick={onClose}>
      <div 
        className="story-viewer-card" 
        onClick={(e) => e.stopPropagation()}
        onMouseDown={() => setIsPaused(true)}
        onMouseUp={() => setIsPaused(false)}
        onTouchStart={() => setIsPaused(true)}
        onTouchEnd={() => setIsPaused(false)}
      >
        {/* BARRAS DE PROGRESO ESTILO INSTAGRAM STORIES */}
        <div className="story-viewer__progress-row">
          {storiesList.map((item, idx) => {
            let widthPct = 0;
            if (idx < currentIndex) widthPct = 100;
            else if (idx === currentIndex) widthPct = progress;
            else widthPct = 0;

            return (
              <div key={item.id || idx} className="story-viewer__progress-track">
                <div 
                  className="story-viewer__progress-fill" 
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            );
          })}
        </div>

        {/* HEADER DE LA HISTORIA */}
        <div className="story-viewer__header">
          <div className="story-viewer__author">
            <div className="story-viewer__avatar">
              <FontAwesomeIcon icon={faTag} />
            </div>
            <div className="story-viewer__meta">
              <h4 className="story-viewer__title">{currentStory.title}</h4>
              <span className="story-viewer__subtitle">Oferta Especial • Promoción</span>
            </div>
          </div>

          <button 
            type="button" 
            className="story-viewer__close-btn" 
            onClick={onClose}
            aria-label="Cerrar historia"
            title="Cerrar historia (Esc)"
          >
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        {/* CONTENEDOR DE MEDIOS Y CONTENIDO */}
        <div className="story-viewer__body" onClick={handleCardClick}>
          {/* FONDO DIFUMINADO AMBIENTAL */}
          {currentStory.img_url && (
            <div 
              className="story-viewer__backdrop-blur" 
              style={{ backgroundImage: `url(${currentStory.img_url})` }}
            />
          )}

          {/* IMAGEN PRINCIPAL (SE AJUSTA COMPLETAMENTE SIN CORTARSE) */}
          <div className="story-viewer__media-box">
            {currentStory.img_url ? (
              <img 
                src={currentStory.img_url} 
                alt={currentStory.title} 
                className="story-viewer__image"
              />
            ) : (
              <div className="story-viewer__no-image">
                <FontAwesomeIcon icon={faTag} size="3x" />
              </div>
            )}
          </div>

          {/* DESCRIPCIÓN / TEXTO DE LA OFERTA (DOCK INFERIOR SIN TAPAR LA IMAGEN) */}
          {currentStory.content && (
            <div 
              className="story-viewer__caption" 
              onClick={(e) => e.stopPropagation()}
            >
              <p>{currentStory.content}</p>
            </div>
          )}
        </div>

        {/* CONTROLES FLECHAS DE NAVEGACIÓN (OPCIONALES PARA DESKTOP) */}
        {storiesList.length > 1 && (
          <>
            {currentIndex > 0 && (
              <button 
                type="button" 
                className="story-viewer__arrow-nav story-viewer__arrow-nav--prev"
                onClick={(e) => { e.stopPropagation(); handlePrev(); }}
                title="Historia anterior"
              >
                <FontAwesomeIcon icon={faChevronLeft} />
              </button>
            )}
            {currentIndex < storiesList.length - 1 && (
              <button 
                type="button" 
                className="story-viewer__arrow-nav story-viewer__arrow-nav--next"
                onClick={(e) => { e.stopPropagation(); handleNext(); }}
                title="Siguiente historia"
              >
                <FontAwesomeIcon icon={faChevronRight} />
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
