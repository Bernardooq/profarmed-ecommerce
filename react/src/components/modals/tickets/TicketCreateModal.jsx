import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTimes, faPaperPlane } from '@fortawesome/free-solid-svg-icons';
import { ticketService } from '../../../services/ticketService';
import { useAuth } from '../../../context/AuthContext';
import { usePermissions } from '../../../hooks/usePermissions';
import { PERMISSIONS } from '../../../config/permissions';
import ErrorMessage from '../../common/ErrorMessage';
import LoadingSpinner from '../../common/LoadingSpinner';

export default function TicketCreateModal({ 
  isOpen, 
  onClose, 
  onTicketCreated, 
  initialOrderId = null,
  lockOrderId = false
}) {
  const { user } = useAuth();
  const { isCustomer, can } = usePermissions();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');
  const [orderId, setOrderId] = useState(initialOrderId ? String(initialOrderId) : '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      if (initialOrderId) {
        setOrderId(String(initialOrderId));
        setTitle(`Incidencia en Pedido #${initialOrderId}`);
      } else {
        setOrderId('');
        setTitle('');
      }
      setDescription('');
      setPriority('medium');
      setError(null);
    }
  }, [isOpen, initialOrderId]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError('Por favor completa todos los campos obligatorios');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const payload = {
        title: title.trim(),
        description: description.trim(),
        priority
      };
      if (orderId && orderId.trim()) {
        const parsed = parseInt(orderId.trim(), 10);
        if (isNaN(parsed) || parsed <= 0) {
          setError('El ID de Pedido debe ser un número válido.');
          setIsSubmitting(false);
          return;
        }
        payload.order_id = parsed;
      }

      const newTicket = await ticketService.createTicket(payload);
      onTicketCreated(newTicket);
      onClose();
    } catch (err) {
      console.error(err);
      setError(err.detail || err.message || 'Error al crear el ticket. Inténtalo más tarde.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal modal--md">
        <div className="modal__header">
          <h2>Abrir Nuevo Ticket de Soporte</h2>
          <button className="modal__close" onClick={onClose} disabled={isSubmitting}>
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        <div className="modal__body">
          {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}
          
          <form id="ticket-create-form" onSubmit={handleSubmit} className="modal__form">
            {lockOrderId ? (
              <div className="form-group">
                <label className="form-group__label">Pedido Vinculado</label>
                <div className="d-flex align-items-center gap-2">
                  <input 
                    type="text" 
                    className="input bg-light font-bold" 
                    value={`Pedido #${orderId}`}
                    disabled
                    readOnly
                  />
                  <span className="badge badge--primary">Bloqueado</span>
                </div>
                <span className="text-xs text-muted">
                  Este ticket se creará directamente asociado a este pedido.
                </span>
              </div>
            ) : !isCustomer ? (
              <div className="form-group">
                <label className="form-group__label">ID de Pedido Vinculado (Opcional)</label>
                <input 
                  type="number" 
                  className="input" 
                  placeholder="Ej. 12 (Solo si el ticket es referente a un pedido)" 
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                  disabled={isSubmitting}
                />
                <span className="text-xs text-muted">
                  Si indicas un pedido, el ticket llegará automáticamente al equipo de Marketing y Admin encargados de ese cliente.
                </span>
              </div>
            ) : null}

            <div className="form-group">
              <label className="form-group__label">Asunto (Breve resumen del problema)</label>
              <input 
                type="text" 
                className="input" 
                placeholder="Ej. Faltante físico de producto en anaquel..." 
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={255}
                required
                disabled={isSubmitting}
              />
            </div>

            <div className="form-group">
              <label className="form-group__label">Prioridad</label>
              <select 
                className="input" 
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                disabled={isSubmitting}
              >
                <option value="low">Baja - No Urgente</option>
                <option value="medium">Media - Normal</option>
                <option value="high">Alta - Urgente</option>
                <option value="urgent">Crítica - Afecta Operación</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-group__label">Descripción detallada</label>
              <textarea 
                className="input" 
                placeholder="Explica a detalle tu problema o solicitud..." 
                rows="5"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
                disabled={isSubmitting}
              ></textarea>
            </div>
          </form>
        </div>

        <div className="modal__footer">
          <button className="btn btn--secondary" onClick={onClose} type="button" disabled={isSubmitting}>Cancelar</button>
          <button className="btn btn--primary" type="submit" form="ticket-create-form" disabled={isSubmitting}>
            {isSubmitting ? <LoadingSpinner size="small" message="Enviando..." /> : <><FontAwesomeIcon icon={faPaperPlane} /> Enviar Ticket</>}
          </button>
        </div>
      </div>
    </div>
  );
}
