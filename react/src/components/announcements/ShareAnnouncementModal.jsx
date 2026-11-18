import { useState, useEffect, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faCopy,
  faDownload,
  faShareNodes,
  faRotateLeft,
  faCheck,
  faExternalLinkAlt,
  faCircleInfo
} from '@fortawesome/free-solid-svg-icons';
import BaseModal from '../common/BaseModal';
import BRAND from '../../config/brand';

const TYPE_HEADERS = {
  popup: 'OFERTA DESTACADA',
  story: 'NOVEDAD EN PROMO',
  footer: 'AVISO PROMOCIONAL',
};

export function WhatsAppIcon({ className = '' }) {
  return (
    <svg
      viewBox="0 0 448 512"
      width="1em"
      height="1em"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-32.6-16.3-54-29.1-75.5-66-5.7-9.8 5.7-9.1 16.3-30.3 1.8-3.7.9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 35.2 15.2 49 16.5 66.6 13.9 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.6z" />
    </svg>
  );
}

function formatPromoDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function buildAnnouncementWhatsAppText(
  item,
  { includeText = true, includeUrl = true } = {}
) {
  if (!item) return '';

  const domain = (BRAND.domain || '').trim();
  const hasValidDomain = Boolean(domain && !domain.includes('ejemplo.com'));

  if (!includeText) {
    return includeUrl && hasValidDomain ? domain : '';
  }

  const headerTitle = TYPE_HEADERS[item.type] || 'PROMOCIÓN ESPECIAL';
  const brandSuffix = BRAND.name ? ` — ${BRAND.name}` : '';
  const header = `*${headerTitle}${brandSuffix}*`;

  const title = (item.title || '').trim();
  const description = (item.content || '').trim();
  const startLabel = formatPromoDate(item.start_date);
  const endLabel = formatPromoDate(item.end_date);

  const lines = [header, ''];

  if (title) {
    lines.push(`*${title}*`);
  }

  if (description) {
    lines.push('', description);
  }

  if (startLabel && endLabel) {
    lines.push('', `• *Vigencia:* Del ${startLabel} al ${endLabel}`);
  } else if (startLabel) {
    lines.push('', `• *Disponible desde:* ${startLabel}`);
  }

  if (includeUrl && hasValidDomain) {
    lines.push('', '*Consulta disponibilidad y realiza tu pedido aquí:*', domain);
  }

  return lines.join('\n');
}

function buildShareSummary({ includeImage, includeText, includeUrl }) {
  const parts = [
    includeImage && 'Imagen',
    includeText && 'Texto',
    includeUrl && 'URL',
  ].filter(Boolean);

  if (parts.length === 0) return 'Selecciona qué enviar';
  if (parts.length === 1) return `Solo ${parts[0]}`;
  if (!includeImage && includeText && includeUrl) return 'Solo Texto + URL';
  return parts.join(' + ');
}

function slugifyFileName(title, id) {
  const clean = (title || `anuncio-${id || 'promo'}`)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return clean || `anuncio-${id || 'promo'}`;
}

async function blobToPngBlob(blob) {
  if (blob.type === 'image/png') return blob;
  const objectUrl = URL.createObjectURL(blob);
  try {
    const img = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = objectUrl;
    });
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(img, 0, 0);
    return await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

async function fetchAnnouncementBlob(item) {
  // Usar query param dedicado (cb=1) desde el primer fetch para no chocar en Chrome
  // con la caché HTTP sin CORS generada por los <img> de la página, evitando usar
  // "cors" porque es un subrecurso reservado de Amazon S3 (403 AccessDenied si CF reenvía query strings).
  const fetchUrl = new URL(item.img_url, window.location.origin);
  if (fetchUrl.protocol === 'http:' || fetchUrl.protocol === 'https:') {
    fetchUrl.searchParams.set('cb', '1');
  }

  try {
    const res = await fetch(fetchUrl.toString(), { mode: 'cors' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.blob();
  } catch (err) {
    if (fetchUrl.toString() === item.img_url) throw err;
    const fallbackRes = await fetch(item.img_url, { mode: 'cors' });
    if (!fallbackRes.ok) throw new Error(`HTTP ${fallbackRes.status}`);
    return await fallbackRes.blob();
  }
}

export default function ShareAnnouncementModal({ item, onClose }) {
  const hasImage = Boolean(item?.img_url);
  const domain = (BRAND.domain || '').trim();
  const hasValidDomain = Boolean(domain && !domain.includes('ejemplo.com'));

  const [includeImage, setIncludeImage] = useState(hasImage);
  const [includeText, setIncludeText] = useState(true);
  const [includeUrl, setIncludeUrl] = useState(hasValidDomain);
  const defaultMessage = useMemo(
    () => buildAnnouncementWhatsAppText(item, { includeText, includeUrl }),
    [item, includeText, includeUrl]
  );
  const [message, setMessage] = useState(defaultMessage);
  const [feedback, setFeedback] = useState(null);
  const [imageState, setImageState] = useState({
    loading: false,
    rawBlob: null,
    pngBlob: null,
    shareFile: null,
    previewUrl: null,
    loadError: false,
    errorDetail: '',
  });

  useEffect(() => {
    setIncludeImage(Boolean(item?.img_url));
    setIncludeText(true);
    setIncludeUrl(hasValidDomain);
  }, [item, hasValidDomain]);

  useEffect(() => {
    setMessage(defaultMessage);
    setFeedback(null);
  }, [defaultMessage]);

  useEffect(() => {
    let active = true;
    let objectUrl = null;
    if (!item?.img_url) {
      setImageState({ loading: false, rawBlob: null, pngBlob: null, shareFile: null, previewUrl: null, loadError: false, errorDetail: '' });
      return () => { active = false; };
    }

    setImageState({ loading: true, rawBlob: null, pngBlob: null, shareFile: null, previewUrl: null, loadError: false, errorDetail: '' });

    (async () => {
      try {
        const rawBlob = await fetchAnnouncementBlob(item);
        const pngBlob = await blobToPngBlob(rawBlob).catch(() => null);
        const fileBlob = pngBlob || rawBlob;
        const ext = pngBlob
          ? 'png'
          : ((rawBlob.type.split('/')[1] || 'png').replace(/[^a-z0-9]/gi, '') || 'png');
        const fileName = `${slugifyFileName(item.title, item.id)}.${ext}`;
        const shareFile = new File([fileBlob], fileName, { type: fileBlob.type || 'image/png' });
        objectUrl = URL.createObjectURL(rawBlob);
        if (!active) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setImageState({ loading: false, rawBlob, pngBlob: fileBlob, shareFile, previewUrl: objectUrl, loadError: false, errorDetail: '' });
      } catch (err) {
        if (!active) return;
        setImageState({
          loading: false,
          rawBlob: null,
          pngBlob: null,
          shareFile: null,
          previewUrl: null,
          loadError: true,
          errorDetail: err?.message || 'Error de red o CORS',
        });
      }
    })();

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item]);

  if (!item) return null;

  const isMobileDevice =
    typeof navigator !== 'undefined' &&
    (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '') ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1));

  // navigator.share en Windows/Desktop envía archivo y texto como 2 mensajes separados en WhatsApp Desktop;
  // en PC usamos portapapeles + wa.me para pegar la imagen con Ctrl+V como caption en un solo mensaje.
  const canShareImageFile = Boolean(
    isMobileDevice &&
    typeof navigator !== 'undefined' &&
    typeof navigator.share === 'function' &&
    imageState.shareFile &&
    typeof navigator.canShare === 'function' &&
    navigator.canShare({ files: [imageState.shareFile] })
  );
  const canClipboardImage =
    typeof navigator !== 'undefined' &&
    Boolean(navigator.clipboard?.write) &&
    typeof ClipboardItem !== 'undefined';

  const notify = (text, type = 'success') => {
    setFeedback({ text, type });
  };

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(message);
      notify('Texto promocional copiado al portapapeles.');
    } catch {
      notify('No se pudo copiar el texto automáticamente. Selecciónalo y cópialo manualmente.', 'warning');
    }
  };

  const handleDownloadImage = () => {
    if (!item.img_url) return;
    const downloadBlob = imageState.pngBlob || imageState.rawBlob;
    if (downloadBlob) {
      const ext = downloadBlob.type === 'image/png'
        ? 'png'
        : ((downloadBlob.type.split('/')[1] || 'webp').replace(/[^a-z0-9]/gi, '') || 'webp');
      const url = URL.createObjectURL(downloadBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${slugifyFileName(item.title, item.id)}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      notify('Imagen descargada correctamente.');
      return;
    }

    window.open(item.img_url, '_blank', 'noopener,noreferrer');
    notify('Se abrió la imagen en una nueva pestaña para que puedas guardarla manualmente.', 'info');
  };

  const handleCopyImage = async () => {
    if (!imageState.pngBlob) {
      notify('No se pudo preparar la imagen para copiar. Usa "Descargar Imagen".', 'warning');
      return;
    }

    if (!canClipboardImage) {
      handleDownloadImage();
      return;
    }

    try {
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': imageState.pngBlob })
      ]);
      notify('Imagen copiada al portapapeles. Pégala en WhatsApp con Ctrl+V.');
    } catch {
      handleDownloadImage();
    }
  };

  const effectiveImage = hasImage && includeImage;
  const trimmedMessage = message.trim();
  const hasMessage = Boolean(trimmedMessage);
  const effectiveUrl = hasValidDomain && includeUrl && hasMessage;
  const effectiveText = includeText || (hasMessage && !effectiveUrl);
  const shareSummary = buildShareSummary({
    includeImage: effectiveImage,
    includeText: effectiveText,
    includeUrl: effectiveUrl,
  });

  const handleShareNative = async () => {
    if (!effectiveImage || !canShareImageFile) return;
    try {
      // Omitir `title` (EXTRA_SUBJECT) en Android ShareSheet para enviar solo archivo + caption como un único mensaje cuando el cliente lo soporta
      const payload = {
        files: [imageState.shareFile],
        ...(hasMessage ? { text: trimmedMessage } : {}),
      };
      await navigator.share(payload);
    } catch (err) {
      if (err?.name !== 'AbortError') {
        notify('No se pudo abrir compartir con imagen. Usa el envío directo por WhatsApp.', 'warning');
      }
    }
  };

  const handleOpenWhatsApp = () => {
    if (!hasMessage) return;
    const waUrl = `https://wa.me/?text=${encodeURIComponent(trimmedMessage)}`;
    let imageCopiedNow = false;

    if (effectiveImage && canClipboardImage && imageState.pngBlob) {
      try {
        navigator.clipboard
          .write([new ClipboardItem({ 'image/png': imageState.pngBlob })])
          .catch(() => {});
        imageCopiedNow = true;
      } catch {
        imageCopiedNow = false;
      }
    }

    window.open(waUrl, '_blank', 'noopener,noreferrer');

    if (effectiveImage && imageCopiedNow) {
      notify('WhatsApp abierto con tu mensaje y la imagen copiada: pega la imagen con Ctrl+V para enviarla con el texto en un mismo mensaje.');
    } else if (effectiveImage) {
      notify('WhatsApp abierto con tu mensaje. Puedes usar "Descargar Imagen" para adjuntarla al mismo mensaje.', 'info');
    }
  };

  const handlePrimarySend = async () => {
    if (effectiveImage && canShareImageFile) {
      await handleShareNative();
      return;
    }
    if (hasMessage) {
      handleOpenWhatsApp();
      return;
    }
    if (effectiveImage) {
      await handleCopyImage();
    }
  };

  const primaryDisabled =
    (!effectiveImage && !hasMessage) ||
    (effectiveImage && !hasMessage && (imageState.loading || imageState.loadError));

  return (
    <BaseModal
      visible={Boolean(item)}
      onClose={onClose}
      size="md"
      title={
        <span className="wa-share__modal-title">
          <WhatsAppIcon className="wa-share__modal-icon" />
          Compartir Anuncio por WhatsApp
        </span>
      }
      footer={
        <div className="wa-share__footer">
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Cerrar
          </button>
          {effectiveImage && canShareImageFile && hasMessage && (
            <button
              type="button"
              className="btn btn--secondary"
              onClick={handleOpenWhatsApp}
              title="Abre WhatsApp directamente solo con el texto y enlace (útil si tu WhatsApp separa texto e imagen al compartir desde el sistema)"
            >
              <WhatsAppIcon />
              Directo WhatsApp (Texto)
              <FontAwesomeIcon icon={faExternalLinkAlt} />
            </button>
          )}
          <button
            type="button"
            className="btn btn--whatsapp"
            onClick={handlePrimarySend}
            disabled={primaryDisabled}
          >
            {effectiveImage && canShareImageFile ? (
              <FontAwesomeIcon icon={faShareNodes} />
            ) : (
              <WhatsAppIcon />
            )}
            {effectiveImage && canShareImageFile
              ? `Enviar ${shareSummary}`
              : hasMessage
                ? `Enviar ${shareSummary}`
                : effectiveImage
                  ? 'Copiar / Descargar Imagen'
                  : shareSummary}
            {(!effectiveImage || !canShareImageFile) && hasMessage && (
              <FontAwesomeIcon icon={faExternalLinkAlt} />
            )}
          </button>
        </div>
      }
    >
      <div className="wa-share">
        {item.status !== 'activo' && (
          <div className="wa-share__notice">
            <FontAwesomeIcon icon={faCircleInfo} />
            <span>Este anuncio figura como <strong>{item.status}</strong>, pero puedes compartirlo igualmente.</span>
          </div>
        )}

        <div className="wa-share__options">
          <span className="wa-share__options-label">¿Qué incluir?</span>
          <div className="wa-share__options-list">
            {hasImage && (
              <label className="wa-share__toggle">
                <input
                  type="checkbox"
                  checked={includeImage}
                  onChange={(e) => setIncludeImage(e.target.checked)}
                />
                <span>Imagen</span>
              </label>
            )}
            <label className="wa-share__toggle">
              <input
                type="checkbox"
                checked={includeText}
                onChange={(e) => setIncludeText(e.target.checked)}
              />
              <span>Texto</span>
            </label>
            {hasValidDomain && (
              <label className="wa-share__toggle">
                <input
                  type="checkbox"
                  checked={includeUrl}
                  onChange={(e) => setIncludeUrl(e.target.checked)}
                />
                <span>Enlace web</span>
              </label>
            )}
          </div>
        </div>

        {hasImage && (
          <div className="wa-share__media">
            <div className={`wa-share__image-wrap ${!includeImage ? 'wa-share__image-wrap--excluded' : ''}`}>
              <img src={imageState.previewUrl || item.img_url} alt={item.title || 'Imagen promocional'} />
            </div>
            <div className="wa-share__media-actions">
              {canClipboardImage && (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={handleCopyImage}
                  disabled={imageState.loading || imageState.loadError}
                >
                  <FontAwesomeIcon icon={faCopy} />
                  {imageState.loading ? 'Preparando imagen...' : 'Copiar Imagen'}
                </button>
              )}
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={handleDownloadImage}
                disabled={imageState.loading}
              >
                <FontAwesomeIcon icon={faDownload} />
                {imageState.loading ? 'Preparando imagen...' : 'Descargar Imagen'}
              </button>
            </div>
            {imageState.loadError ? (
              <p className="wa-share__hint">
                No se pudo copiar la imagen al portapapeles ({imageState.errorDetail || 'bloqueo CORS o archivo no disponible'}). Usa &quot;Descargar Imagen&quot; para abrirla/guardarla y adjuntarla en WhatsApp.
              </p>
            ) : (
              <p className="wa-share__hint">
                {!includeImage
                  ? 'Imagen desmarcada: solo se enviará el mensaje configurado abajo.'
                  : canShareImageFile
                    ? 'Si tu WhatsApp móvil separa el texto de la imagen al compartir archivo, usa "Copiar Texto" o "Directo WhatsApp (Texto)".'
                    : 'En PC se copia la imagen y se abre WhatsApp con el mensaje: pega con Ctrl+V para enviar imagen y texto en un solo mensaje.'}
              </p>
            )}
          </div>
        )}

        <div className="wa-share__message-section">
          <div className="wa-share__message-header">
            <label htmlFor="wa-share-text">Mensaje prehecho para WhatsApp</label>
            <div className="wa-share__message-tools">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  setMessage(defaultMessage);
                  setFeedback(null);
                }}
                title="Restaurar mensaje original"
                disabled={!includeText && !includeUrl}
              >
                <FontAwesomeIcon icon={faRotateLeft} /> Restaurar
              </button>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={handleCopyText}
                disabled={!hasMessage}
              >
                <FontAwesomeIcon icon={faCopy} /> Copiar Texto
              </button>
            </div>
          </div>

          <textarea
            id="wa-share-text"
            className="input wa-share__textarea"
            rows={8}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Sin texto ni enlace (se enviará solo la imagen, o escribe un pie de foto aquí)..."
          />
        </div>

        {feedback && (
          <div className={`wa-share__feedback wa-share__feedback--${feedback.type}`}>
            <FontAwesomeIcon icon={feedback.type === 'success' ? faCheck : faCircleInfo} />
            <span>{feedback.text}</span>
          </div>
        )}
      </div>
    </BaseModal>
  );
}
