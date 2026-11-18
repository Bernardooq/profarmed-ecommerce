import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFileAlt, faFileArchive, faDownload, faSpinner } from '@fortawesome/free-solid-svg-icons';

export default function ModalDownloadTxtOptions({ visible, order, onClose, onConfirm }) {
  const [downloadMode, setDownloadMode] = useState('all');
  const [chunkSize, setChunkSize] = useState(10);
  const [loading, setLoading] = useState(false);

  if (!visible || !order) return null;

  const totalItems = order.items_count !== undefined ? order.items_count : (order.items?.length || 0);
  const parsedChunk = parseInt(chunkSize, 10) || 0;

  let fileCount = 1;
  if (downloadMode === 'split' && parsedChunk > 0 && totalItems > 0) {
    fileCount = Math.ceil(totalItems / parsedChunk);
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const itemsPerFile = downloadMode === 'split' ? parsedChunk : null;
      await onConfirm(order.order_id, itemsPerFile);
      onClose();
    } catch (err) {
      console.error('Error al descargar archivo(s) TXT:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--md" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3>
            <FontAwesomeIcon icon={faFileAlt} className="mr-2 text-primary" />
            Descargar Pedido TXT (ERP)
          </h3>
          <button className="modal__close" onClick={onClose} aria-label="Cerrar modal" disabled={loading}>
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal__body modal-download-txt">
            <div className="modal-download-txt__info-banner">
              <strong>Pedido #{order.order_id}</strong> &bull; {totalItems} {totalItems === 1 ? 'artículo' : 'artículos'} en total.
            </div>

            <div className="modal-download-txt__options">
              <label className={`modal-download-txt__option-card ${downloadMode === 'all' ? 'modal-download-txt__option-card--selected' : ''}`}>
                <input
                  type="radio"
                  name="downloadMode"
                  value="all"
                  checked={downloadMode === 'all'}
                  onChange={() => setDownloadMode('all')}
                />
                <div className="modal-download-txt__option-content">
                  <div className="modal-download-txt__option-title">Un solo archivo completo</div>
                  <div className="modal-download-txt__option-desc">
                    Descarga todos los {totalItems} artículos en <code>pedido_{order.order_id}.txt</code>
                  </div>
                </div>
              </label>

              <label className={`modal-download-txt__option-card ${downloadMode === 'split' ? 'modal-download-txt__option-card--selected' : ''}`}>
                <input
                  type="radio"
                  name="downloadMode"
                  value="split"
                  checked={downloadMode === 'split'}
                  onChange={() => setDownloadMode('split')}
                />
                <div className="modal-download-txt__option-content">
                  <div className="modal-download-txt__option-title">Dividir por partes (ej. de 4 en 4, 5 en 5, 10 en 10)</div>
                  <div className="modal-download-txt__option-desc">
                    Divide el pedido en archivos TXT más pequeños para cargarlos por partes al ERP.
                  </div>
                </div>
              </label>
            </div>

            {downloadMode === 'split' && (
              <div className="modal-download-txt__chunk-box">
                <div className="form-group">
                  <label htmlFor="chunk-size-input" className="form-group__label">
                    Cantidad de productos por archivo TXT:
                  </label>
                  <input
                    id="chunk-size-input"
                    type="number"
                    className="input modal-download-txt__chunk-input"
                    min="1"
                    max="500"
                    value={chunkSize}
                    onChange={(e) => setChunkSize(e.target.value)}
                    required
                  />
                </div>

                <div className="modal-download-txt__preview-info">
                  <div>
                    <FontAwesomeIcon icon={faFileArchive} className="mr-1 text-warning" />
                    Se generará <strong>1 archivo ZIP</strong> comprimido (<code>pedido_{order.order_id}_partes.zip</code>) con <strong>{fileCount} {fileCount === 1 ? 'archivo TXT' : 'archivos TXT'}</strong>:
                    <div className="mt-1">
                      <code>{fileCount === 1 ? `pedido_${order.order_id}_1.txt` : `pedido_${order.order_id}_1.txt, pedido_${order.order_id}_2.txt ... pedido_${order.order_id}_${fileCount}.txt`}</code>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="modal__footer">
            <button type="button" className="btn btn--secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--primary" disabled={loading || (downloadMode === 'split' && parsedChunk <= 0)}>
              {loading ? (
                <>
                  <FontAwesomeIcon icon={faSpinner} spin className="mr-2" />
                  Generando...
                </>
              ) : (
                <>
                  <FontAwesomeIcon icon={faDownload} className="mr-2" />
                  Descargar {downloadMode === 'split' ? 'ZIP' : 'TXT'}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
