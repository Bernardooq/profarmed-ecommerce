import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faCartShopping, faUser, faBoxOpen,
  faShieldHalved, faLock
} from '@fortawesome/free-solid-svg-icons';

export default function LedgerTimelineTab({
  split,
  splitCode,
  splitId,
  orderAuditData,
  hasContainers,
  totalProducts,
  totalPickedUnits,
  totalCheckedUnits,
  totalLaserUnits,
  totalBoxUnits,
  totalManualUnits,
  isBalanced,
  isFilter2Omitted = false
}) {
  return (
    <div className="audit-timeline">
      {/* Paso 1: Liberación a Bodega */}
      <div className="audit-timeline__step">
        <div className="audit-timeline__icon audit-timeline__icon--done">
          <FontAwesomeIcon icon={faCartShopping} />
        </div>
        <div className="audit-timeline__body">
          <div className="audit-timeline__header">
            <h5>1. Liberación y Enrutamiento a Bodega</h5>
            <span className="timeline-time">
              {orderAuditData?.order?.created_at
                ? new Date(orderAuditData.order.created_at).toLocaleString()
                : 'Registrado'}
            </span>
          </div>
          <p className="audit-timeline__desc">
            El pedido fue confirmado y dividido en Split #{split?.split_number ?? 1} ({splitCode || splitId?.substring(0, 8)}) para preparación en almacén.
          </p>
          <div className="audit-timeline__meta">
            <span className="badge badge--dark text-primary font-mono">
              Modalidad: {hasContainers ? '🧺 Canastas QR' : '📦 Surtido Directo'}
            </span>
            <span className="badge badge--dark">Total SKUs: {totalProducts}</span>
            <span className="badge badge--dark">Unidades Requeridas: {totalPickedUnits} pz</span>
          </div>
        </div>
      </div>

      {/* Paso 2: Inicio de Surtido en Piso */}
      <div className="audit-timeline__step">
        <div className={`audit-timeline__icon ${split?.started_at ? 'audit-timeline__icon--done' : 'audit-timeline__icon--pending'}`}>
          <FontAwesomeIcon icon={faUser} />
        </div>
        <div className="audit-timeline__body">
          <div className="audit-timeline__header">
            <h5>2. Inicio de Surtido (1er Filtro)</h5>
            <span className="timeline-time">
              {split?.started_at ? new Date(split.started_at).toLocaleString() : 'Pendiente'}
            </span>
          </div>
          <p className="audit-timeline__desc">
            {split?.picker_name ? (
              <>El surtidor <strong>{split.picker_name}</strong> tomó la orden y comenzó la recolección en estanterías.</>
            ) : (
              'En espera de ser tomado por un operador de surtido en pasillos.'
            )}
          </p>
          {split?.started_at && (
            <div className="audit-timeline__meta">
              <span className="badge badge--success">✓ Inicio registrado</span>
            </div>
          )}
        </div>
      </div>

      {/* Paso 3: Cierre de Surtido en Piso */}
      <div className="audit-timeline__step">
        <div className={`audit-timeline__icon ${split?.completed_at ? 'audit-timeline__icon--done' : (split?.started_at ? 'audit-timeline__icon--active' : 'audit-timeline__icon--pending')}`}>
          <FontAwesomeIcon icon={faBoxOpen} />
        </div>
        <div className="audit-timeline__body">
          <div className="audit-timeline__header">
            <h5>3. Finalización de Surtido y Entrega a Mesa de Control</h5>
            <span className="timeline-time">
              {split?.completed_at ? new Date(split.completed_at).toLocaleString() : (split?.started_at ? 'En recolección...' : 'Pendiente')}
            </span>
          </div>
          <p className="audit-timeline__desc">
            {split?.completed_at ? (
              <>
                Se completó la recolección física de <strong>{totalPickedUnits} piezas</strong> en pasillos con una duración total de <strong>{split?.duration_formatted || 'N/A'}</strong>.
              </>
            ) : (
              'El operador continúa recolectando partidas en los pasillos de bodega.'
            )}
          </p>
          <div className="audit-timeline__meta">
            <span className="audit-method-tag audit-method-tag--laser">
              🔫 Láser: {totalLaserUnits} pz
            </span>
            <span className="audit-method-tag audit-method-tag--box">
              📦 Cajas: {totalBoxUnits} pz
            </span>
            <span className="audit-method-tag audit-method-tag--manual">
              ✍️ Manual: {totalManualUnits} pz
            </span>
          </div>
        </div>
      </div>

      {/* Paso 4: Revisión 2do Filtro */}
      <div className="audit-timeline__step">
        <div className={`audit-timeline__icon ${split?.audited_at || split?.checking_completed_at || (split?.status === 'checked' || split?.status === 'completed') || isFilter2Omitted ? 'audit-timeline__icon--done' : (split?.checking_started_at ? 'audit-timeline__icon--active' : 'audit-timeline__icon--pending')}`}>
          <FontAwesomeIcon icon={faShieldHalved} />
        </div>
        <div className="audit-timeline__body">
          <div className="audit-timeline__header">
            <h5>4. Revisión en Mesa de Control (2do Filtro)</h5>
            <span className="timeline-time">
              {split?.checking_started_at
                ? new Date(split.checking_started_at).toLocaleString()
                : isFilter2Omitted
                  ? 'Salida Directa'
                  : 'Pendiente'}
            </span>
          </div>
          <p className="audit-timeline__desc">
            {split?.checker_name && split.checker_name !== 'Sin asignar' ? (
              <>
                El revisor <strong>{split.checker_name}</strong> validó en estación de verificación láser.
                {split?.checking_duration_formatted && (
                  <> Tiempo de revisión: <strong>{split.checking_duration_formatted}</strong>.</>
                )}
              </>
            ) : isFilter2Omitted ? (
              'El pedido completó su proceso de surtido y fue sellado directamente sin requerir paso por la estación de 2do filtro.'
            ) : (
              'El paquete o canastas están pendientes de ingresar a la estación láser de verificación ciega.'
            )}
          </p>
          <div className="audit-timeline__meta">
            <span className={`badge ${isFilter2Omitted ? 'badge--info' : isBalanced ? 'badge--success' : 'badge--warning'}`}>
              {isFilter2Omitted
                ? `✓ Salida Directa (${totalPickedUnits} de ${totalPickedUnits} pz)`
                : isBalanced
                  ? '✓ Verificación Coincidente'
                  : `${totalCheckedUnits} de ${totalPickedUnits} pz auditadas`}
            </span>
          </div>
        </div>
      </div>

      {/* Paso 5: Sellado Inviolable y Despacho */}
      <div className="audit-timeline__step">
        <div className={`audit-timeline__icon ${split?.security_seal_folio ? 'audit-timeline__icon--done' : 'audit-timeline__icon--pending'}`}>
          <FontAwesomeIcon icon={faLock} />
        </div>
        <div className="audit-timeline__body">
          <div className="audit-timeline__header">
            <h5>5. Sellado de Seguridad y Preparación para Envío</h5>
            <span className="timeline-time">
              {split?.audited_at
                ? new Date(split.audited_at).toLocaleString()
                : split?.completed_at
                  ? new Date(split.completed_at).toLocaleString()
                  : 'Pendiente'}
            </span>
          </div>
          <p className="audit-timeline__desc">
            {split?.security_seal_folio ? (
              <>
                Empaque consolidado y asegurado con cincho inviolable <strong>Folio #{split.security_seal_folio}</strong>. Listo para transferirse a la zona de embarques y logística.
              </>
            ) : (
              'Pendiente de consolidar empaques físicos y colocar precinto inviolable.'
            )}
          </p>
          {split?.security_seal_folio && (
            <div className="audit-timeline__meta">
              <span className="badge badge--success">Cincho #{split.security_seal_folio} Verificado</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
