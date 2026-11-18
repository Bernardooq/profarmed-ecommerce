import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faListOl } from '@fortawesome/free-solid-svg-icons';

export default function ItemsPerPageSelector() {
  const { limit, changeLimit } = usePaginationLimit();

  return (
    <div className="items-per-page-selector" title="Elementos por página">
      <label htmlFor="itemsPerPageSelect" className="items-per-page-selector__label">
        <FontAwesomeIcon icon={faListOl} className="items-per-page-selector__icon" />
        <span className="items-per-page-selector__label-text">Mostrar:</span>
      </label>
      <select
        id="itemsPerPageSelect"
        className="items-per-page-selector__select"
        value={limit}
        onChange={(e) => changeLimit(e.target.value)}
        aria-label="Elementos por página"
      >
        <option value={10}>10 por pág.</option>
        <option value={20}>20 por pág.</option>
        <option value={50}>50 por pág.</option>
        <option value={100}>100 por pág.</option>
        <option value={150}>150 por pág.</option>
        <option value={190}>190 por pág. (Máx)</option>
      </select>
    </div>
  );
}
