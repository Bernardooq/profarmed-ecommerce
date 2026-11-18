import React, { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faQrcode, faCopy, faCheck, faDownload, faPrint,
  faTimes, faBoxesStacked, faCircleCheck
} from '@fortawesome/free-solid-svg-icons';

/**
 * ModalContainerQR.jsx
 * Modal para visualizar, descargar, imprimir y copiar directamente como imagen PNG
 * la etiqueta con código QR de una canasta física (Tote de Bodega).
 */
export default function ModalContainerQR({ container, isOpen, onClose }) {
  const canvasRef = useRef(null);
  const [copyFeedback, setCopyFeedback] = useState(null);
  const [copyingImage, setCopyingImage] = useState(false);
  const [generating, setGenerating] = useState(true);

  useEffect(() => {
    if (!isOpen || !container || !canvasRef.current) return;

    setGenerating(true);
    setCopyFeedback(null);

    QRCode.toCanvas(
      canvasRef.current,
      container.qr_code,
      {
        width: 280,
        margin: 2,
        color: {
          dark: '#0f172a',
          light: '#ffffff'
        },
        errorCorrectionLevel: 'H'
      },
      (error) => {
        setGenerating(false);
        if (error) {
          console.error('Error generando QR:', error);
        }
      }
    );
  }, [isOpen, container]);

  if (!isOpen || !container) return null;

  // 1. Copiar imagen real PNG directamente al portapapeles del sistema
  const handleCopyImageToClipboard = async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      setCopyingImage(true);
      canvas.toBlob(async (blob) => {
        if (!blob) {
          setCopyFeedback({ type: 'error', text: 'No se pudo generar el mapa de bits.' });
          setCopyingImage(false);
          return;
        }

        try {
          if (navigator.clipboard && window.ClipboardItem) {
            await navigator.clipboard.write([
              new ClipboardItem({ 'image/png': blob })
            ]);
            setCopyFeedback({
              type: 'success',
              text: '¡Imagen QR copiada al portapapeles! Puedes pegarla directamente con Ctrl+V.'
            });
          } else {
            throw new Error('ClipboardItem no soportado en este navegador');
          }
        } catch (clipErr) {
          // Fallback a descarga automática si el navegador no permite ClipboardItem
          handleDownloadPng();
          setCopyFeedback({
            type: 'info',
            text: 'Descargando imagen PNG (tu navegador no permite escribir imágenes al portapapeles).'
          });
        } finally {
          setCopyingImage(false);
          setTimeout(() => setCopyFeedback(null), 4000);
        }
      }, 'image/png');
    } catch (err) {
      setCopyingImage(false);
      setCopyFeedback({ type: 'error', text: err.message || 'Error al copiar imagen.' });
      setTimeout(() => setCopyFeedback(null), 4000);
    }
  };

  // 2. Descargar archivo PNG
  const handleDownloadPng = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = `QR_${container.qr_code}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // 3. Imprimir etiqueta adhesiva física para rotular canasta
  const handlePrintLabel = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL('image/png');

    const printWindow = window.open('', '_blank', 'width=500,height=600');
    if (!printWindow) {
      alert('Por favor permite ventanas emergentes para imprimir la etiqueta.');
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Etiqueta Tote ${container.qr_code}</title>
          <style>
            @page {
              size: auto;
              margin: 8mm;
            }
            body {
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
              margin: 0;
              padding: 10px;
              display: flex;
              justify-content: center;
              align-items: center;
              min-height: 100vh;
              box-sizing: border-box;
            }
            .label-card {
              border: 3px solid #0f172a;
              border-radius: 12px;
              padding: 16px;
              text-align: center;
              width: 300px;
              background: #fff;
            }
            .label-brand {
              font-size: 14px;
              font-weight: 800;
              letter-spacing: 2px;
              color: #475569;
              text-transform: uppercase;
              margin-bottom: 4px;
            }
            .label-title {
              font-size: 26px;
              font-weight: 900;
              color: #0f172a;
              font-family: monospace;
              letter-spacing: 1px;
              margin: 4px 0 12px 0;
            }
            .label-qr img {
              width: 220px;
              height: 220px;
              display: block;
              margin: 0 auto;
            }
            .label-footer {
              margin-top: 10px;
              font-size: 11px;
              color: #64748b;
              font-weight: 600;
              border-top: 1px dashed #cbd5e1;
              padding-top: 8px;
            }
          </style>
        </head>
        <body>
          <div class="label-card">
            <div class="label-brand">FARMA-B2B WMS</div>
            <div class="label-title">🧺 ${container.qr_code}</div>
            <div class="label-qr">
              <img src="${dataUrl}" alt="QR ${container.qr_code}" />
            </div>
            <div class="label-footer">
              CANASTA REUTILIZABLE DE BODEGA<br/>
              FOLIO: ${container.container_id}
            </div>
          </div>
          <script>
            window.onload = function() {
              window.print();
              setTimeout(function() { window.close(); }, 500);
            };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // 4. Copiar texto de código QR
  const handleCopyText = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(container.qr_code);
      setCopyFeedback({ type: 'success', text: `Texto '${container.qr_code}' copiado.` });
      setTimeout(() => setCopyFeedback(null), 3000);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2">
            <FontAwesomeIcon icon={faQrcode} className="text-primary" />
            <span>Código QR — Canasta {container.qr_code}</span>
          </h3>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar">
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        <div className="modal__body text-center">
          {copyFeedback && (
            <div className={`alert alert--${copyFeedback.type === 'error' ? 'danger' : 'success'} py-2 px-3 text-xs mb-3`}>
              <FontAwesomeIcon icon={faCircleCheck} className="me-1" />
              {copyFeedback.text}
            </div>
          )}

          <div
            className="p-3 bg-white rounded-lg shadow-inner d-inline-block border mx-auto mb-3"
            style={{ minHeight: '300px' }}
          >
            <canvas ref={canvasRef} style={{ display: 'block', maxWidth: '100%' }} />
          </div>

          <div className="mb-3">
            <div className="font-mono text-lg font-bold text-dark">
              {container.qr_code}
            </div>
            <div className="text-muted text-xs font-mono">
              ID UUID: {container.container_id}
            </div>
            <div className="mt-1">
              {container.status === 'available' && (
                <span className="badge badge--success">🟢 Disponible (Vacía)</span>
              )}
              {container.status === 'in_use' && (
                <span className="badge badge--primary">🔵 En Uso Activo</span>
              )}
              {container.status === 'maintenance' && (
                <span className="badge badge--warning">🟡 En Mantenimiento</span>
              )}
            </div>
          </div>

          <div className="d-flex flex-wrap gap-2 justify-content-center">
            {/* Copiar Imagen Directa al Portapapeles */}
            <button
              type="button"
              className="btn btn--primary font-bold"
              onClick={handleCopyImageToClipboard}
              disabled={copyingImage || generating}
              title="Copiar imagen PNG directamente al portapapeles para pegar con Ctrl+V"
            >
              <FontAwesomeIcon icon={faCopy} className="me-1" />
              {copyingImage ? 'Copiando imagen...' : 'Copiar Imagen QR'}
            </button>

            {/* Descargar PNG */}
            <button
              type="button"
              className="btn btn--secondary"
              onClick={handleDownloadPng}
              disabled={generating}
              title="Descargar imagen del código QR en archivo PNG"
            >
              <FontAwesomeIcon icon={faDownload} className="me-1" />
              Descargar PNG
            </button>

            {/* Imprimir Etiqueta */}
            <button
              type="button"
              className="btn btn--secondary"
              onClick={handlePrintLabel}
              disabled={generating}
              title="Imprimir etiqueta adhesiva física para la canasta"
            >
              <FontAwesomeIcon icon={faPrint} className="me-1" />
              Imprimir Etiqueta
            </button>

            {/* Copiar texto */}
            <button
              type="button"
              className="btn btn--ghost btn--sm text-muted"
              onClick={handleCopyText}
              title="Copiar solo el código de texto"
            >
              Copiar Folio Texto
            </button>
          </div>
        </div>

        <div className="modal__footer">
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
