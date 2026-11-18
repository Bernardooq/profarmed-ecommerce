import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBackward, faForward } from '@fortawesome/free-solid-svg-icons';

export default function PaginationButtons({
  onPrev,
  onNext,
  canGoPrev = true,
  canGoNext = true,
  currentPage: explicitCurrentPage,
  page,
  lookaheadPages = undefined,
  onPageChange
}) {
  const currentPage = explicitCurrentPage !== undefined ? explicitCurrentPage : (page ?? 0);
  const isLookahead = lookaheadPages !== undefined && lookaheadPages !== null;

  if (!isLookahead) {
    // Legacy mode: Anterior / Siguiente buttons only
    return (
      <nav className="pagination" aria-label="Paginación">
        <button
          className="pagination__btn"
          onClick={(e) => {
            if (onPrev) onPrev(e);
            setTimeout(() => window.scrollTo(0, 0), 10);
          }}
          disabled={!canGoPrev}
          aria-label="Página anterior"
        >
          <FontAwesomeIcon icon={faBackward} /> <span className="pagination__btn-text">Anterior</span>
        </button>

        <button
          className="pagination__btn"
          onClick={(e) => {
            if (onNext) onNext(e);
            setTimeout(() => window.scrollTo(0, 0), 10);
          }}
          disabled={!canGoNext}
          aria-label="Página siguiente"
        >
          <span className="pagination__btn-text">Siguiente</span> <FontAwesomeIcon icon={faForward} />
        </button>
      </nav>
    );
  }

  // Lookahead Numeric Mode
  const visiblePages = [];
  const startPage = Math.max(0, currentPage - 2);
  const endPage = currentPage + lookaheadPages;

  for (let i = startPage; i <= endPage; i++) {
    visiblePages.push(i);
  }

  const handlePageClick = (p) => {
    if (onPageChange && p !== currentPage) {
      onPageChange(p);
      setTimeout(() => window.scrollTo(0, 0), 10);
    }
  };

  return (
    <nav className="pagination" aria-label="Paginación">
      {/* Anterior */}
      <button
        className="pagination__btn"
        onClick={() => handlePageClick(currentPage - 1)}
        disabled={currentPage === 0}
        aria-label="Página anterior"
      >
        <FontAwesomeIcon icon={faBackward} /> <span className="pagination__btn-text">Anterior</span>
      </button>

      {/* First page button & ellipsis if startPage > 0 */}
      {startPage > 0 && (
        <>
          <button
            className="pagination__btn"
            onClick={() => handlePageClick(0)}
          >
            1
          </button>
          {startPage > 1 && (
            <span className="pagination__ellipsis">...</span>
          )}
        </>
      )}

      {/* Numeric page buttons */}
      {visiblePages.map((p) => (
        <button
          key={p}
          className={`pagination__btn ${currentPage === p ? 'pagination__btn--active' : ''}`}
          onClick={() => handlePageClick(p)}
          aria-current={currentPage === p ? 'page' : undefined}
        >
          {p + 1}
        </button>
      ))}

      {/* Future ellipsis if lookaheadPages has hit or exceeded maximum (e.g. 5) */}
      {lookaheadPages >= 5 && (
        <span className="pagination__ellipsis">...</span>
      )}

      {/* Siguiente */}
      <button
        className="pagination__btn"
        onClick={() => handlePageClick(currentPage + 1)}
        disabled={lookaheadPages === 0}
        aria-label="Página siguiente"
      >
        <span className="pagination__btn-text">Siguiente</span> <FontAwesomeIcon icon={faForward} />
      </button>
    </nav>
  );
}