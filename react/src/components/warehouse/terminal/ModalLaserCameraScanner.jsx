import { useState, useEffect, useRef } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCamera, faTimes, faLightbulb, faCheckCircle, faExclamationTriangle } from '@fortawesome/free-solid-svg-icons';

export default function ModalLaserCameraScanner({
  isOpen,
  onClose,
  onScan,
  activeContainerQr,
  usesContainers,
  isSegundoFiltro
}) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const animationFrameRef = useRef(null);
  const lastScannedCodeRef = useRef('');
  const lastScannedTimeRef = useRef(0);

  const [hasCamera, setHasCamera] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [hasTorch, setHasTorch] = useState(false);
  const [lastDetected, setLastDetected] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [supportedFormats, setSupportedFormats] = useState([]);
  const [hasBarcodeDetector, setHasBarcodeDetector] = useState(true);

  useEffect(() => {
    if (!isOpen) {
      stopCamera();
      return;
    }

    startCamera();

    return () => {
      stopCamera();
    };
  }, [isOpen]);

  const startCamera = async () => {
    setErrorMessage(null);
    setLastDetected(null);
    lastScannedCodeRef.current = '';

    if (!navigator?.mediaDevices?.getUserMedia) {
      setHasCamera(false);
      setErrorMessage('Este navegador o dispositivo no soporta acceso a la cámara mediante HTTPS.');
      return;
    }

    // Comprobar soporte nativo de BarcodeDetector
    let barcodeDetector = null;
    if ('BarcodeDetector' in window) {
      try {
        const supported = await window.BarcodeDetector.getSupportedFormats();
        setSupportedFormats(supported);
        barcodeDetector = new window.BarcodeDetector({
          formats: supported.length > 0 ? supported : ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e']
        });
        setHasBarcodeDetector(true);
      } catch (e) {
        console.warn('BarcodeDetector error:', e);
        setHasBarcodeDetector(false);
      }
    } else {
      setHasBarcodeDetector(false);
    }

    try {
      const constraints = {
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }

      // Comprobar soporte de linterna (torch)
      const track = stream.getVideoTracks()[0];
      if (track && typeof track.getCapabilities === 'function') {
        const capabilities = track.getCapabilities();
        if (capabilities.torch) {
          setHasTorch(true);
        }
      }

      // Iniciar bucle de detección en frames de video
      if (barcodeDetector) {
        startDetectionLoop(barcodeDetector);
      }
    } catch (err) {
      console.error('Error starting camera scanner:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMessage('Permiso de cámara denegado. Permite el acceso a la cámara en los ajustes del navegador para escanear.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setErrorMessage('No se encontró ninguna cámara trasera en este dispositivo.');
      } else {
        setErrorMessage(`No se pudo inicializar la cámara: ${err.message || 'Error desconocido'}`);
      }
    }
  };

  const stopCamera = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {}
      });
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setTorchEnabled(false);
    setHasTorch(false);
  };

  const toggleTorch = async () => {
    if (!streamRef.current) return;
    const track = streamRef.current.getVideoTracks()[0];
    if (track) {
      try {
        const nextTorch = !torchEnabled;
        await track.applyConstraints({
          advanced: [{ torch: nextTorch }]
        });
        setTorchEnabled(nextTorch);
      } catch (e) {
        console.warn('Torch toggle error:', e);
      }
    }
  };

  const startDetectionLoop = (detector) => {
    let isDetecting = false;

    const detectFrame = async () => {
      if (!videoRef.current || videoRef.current.readyState < 2) {
        animationFrameRef.current = requestAnimationFrame(detectFrame);
        return;
      }

      if (!isDetecting) {
        isDetecting = true;
        try {
          const barcodes = await detector.detect(videoRef.current);
          if (barcodes && barcodes.length > 0) {
            const rawCode = barcodes[0].rawValue?.trim();
            const now = Date.now();

            // Evitar re-disparo del mismo código durante 1.5s, pero permitir si es código diferente
            if (rawCode && (rawCode !== lastScannedCodeRef.current || (now - lastScannedTimeRef.current) > 1500)) {
              lastScannedCodeRef.current = rawCode;
              lastScannedTimeRef.current = now;

              setLastDetected(rawCode);
              setIsProcessing(true);

              if (typeof navigator !== 'undefined' && navigator.vibrate) {
                try { navigator.vibrate(60); } catch {}
              }

              // Llamar al handler principal
              if (onScan) {
                await onScan(rawCode);
              }

              setTimeout(() => {
                setIsProcessing(false);
              }, 600);
            }
          }
        } catch (e) {
          // Frame skip
        } finally {
          isDetecting = false;
        }
      }

      animationFrameRef.current = requestAnimationFrame(detectFrame);
    };

    animationFrameRef.current = requestAnimationFrame(detectFrame);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="modal warehouse-camera-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__header">
          <div className="d-flex align-items-center gap-2">
            <FontAwesomeIcon icon={faCamera} className="text-primary" />
            <h3 className="m-0 text-base">
              Escáner de Cámara Láser
            </h3>
          </div>
          <button
            type="button"
            className="modal__close"
            onClick={onClose}
            aria-label="Cerrar escáner de cámara"
          >
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        <div className="modal__body p-0 warehouse-camera-modal__body">
          {/* HUD Superior Informativo */}
          <div className="warehouse-camera-modal__hud">
            {usesContainers ? (
              activeContainerQr ? (
                <span>
                  🧺 Canasta Activa: <strong className="text-warning font-mono">{activeContainerQr}</strong> (Apunta al producto o a otra canasta)
                </span>
              ) : (
                <span className="text-warning font-bold">
                  ⚠️ Apunta la cámara al código QR de una canasta antes de productos
                </span>
              )
            ) : (
              <span>
                ⚡ Apunta la cámara al código de barras del producto {isSegundoFiltro ? '(Revisión 2do Filtro)' : '(Surtido)'}
              </span>
            )}
          </div>

          {/* Visor de Video */}
          <div className="warehouse-camera-modal__viewport">
            {errorMessage ? (
              <div className="p-4 text-center text-white">
                <FontAwesomeIcon icon={faExclamationTriangle} className="text-warning text-3xl mb-3" />
                <p className="text-sm m-0 mb-3">{errorMessage}</p>
                {!hasBarcodeDetector && (
                  <p className="text-xs text-muted">
                    Nota: Se requiere Google Chrome, Microsoft Edge o un navegador compatible con BarcodeDetector para escaneo por cámara en tiempo real.
                  </p>
                )}
                <button type="button" className="btn btn--primary btn--sm" onClick={startCamera}>
                  Reintentar Cámara
                </button>
              </div>
            ) : (
              <>
                <video
                  ref={videoRef}
                  playsInline
                  autoPlay
                  muted
                  className="warehouse-camera-modal__video"
                />

                {/* Retícula de Enfoque con Línea Láser Animada */}
                <div
                  className={`warehouse-camera-modal__reticle ${isProcessing ? 'warehouse-camera-modal__reticle--active' : ''}`}
                >
                  <div
                    className={`warehouse-camera-modal__laser-line ${isProcessing ? 'warehouse-camera-modal__laser-line--active' : ''}`}
                  />
                  {lastDetected && (
                    <span className="warehouse-camera-modal__badge">
                      ✓ {lastDetected}
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Barra de Acciones del Escáner */}
          <div className="warehouse-camera-modal__footer">
            {hasTorch && (
              <button
                type="button"
                className={`btn btn--sm ${torchEnabled ? 'btn--warning' : 'btn--ghost'}`}
                onClick={toggleTorch}
                title="Encender o apagar linterna de la cámara"
              >
                <FontAwesomeIcon icon={faLightbulb} /> {torchEnabled ? 'Linterna ON' : 'Linterna'}
              </button>
            )}

            <span className="text-xs text-muted text-truncate">
              {isProcessing ? '⚡ Procesando escaneo...' : 'Apunta el código dentro del marco'}
            </span>

            <button type="button" className="btn btn--outline btn--sm" onClick={onClose}>
              Finalizar Cámara
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
