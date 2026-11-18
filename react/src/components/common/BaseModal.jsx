import { useEffect } from 'react';

/**
 * Componente Base Universal para Modales.
 * Encapsula overlay, contenedor, animaciones, cierre con tecla ESC, click fuera y footer opcional.
 *
 * Props:
 * - visible: boolean
 * - onClose: () => void
 * - title: string | ReactNode
 * - size: 'sm' | 'md' | 'lg' | 'xl' | 'full' (default: 'md')
 * - footer: ReactNode (opcional)
 * - children: ReactNode
 */
export default function BaseModal({
    visible,
    onClose,
    title,
    size = 'md',
    footer = null,
    children,
    className = ''
}) {
    // Cerrar con tecla Escape
    useEffect(() => {
        if (!visible) return;
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose?.();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [visible, onClose]);

    if (!visible) return null;

    return (
        <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
            <div
                className={`modal modal--${size} ${className}`}
                onClick={(e) => e.stopPropagation()}
            >
                {title && (
                    <div className="modal__header">
                        <h2>{title}</h2>
                        <button
                            type="button"
                            className="modal__close"
                            onClick={onClose}
                            aria-label="Cerrar modal"
                        >
                            &times;
                        </button>
                    </div>
                )}

                <div className="modal__body">
                    {children}
                </div>

                {footer && (
                    <div className="modal__footer">
                        {footer}
                    </div>
                )}
            </div>
        </div>
    );
}
