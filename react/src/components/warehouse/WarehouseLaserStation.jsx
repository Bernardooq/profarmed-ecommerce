import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import warehouseService from '../../services/warehouseService';
import LoadingSpinner from '../common/LoadingSpinner';
import { playScanSuccessSound, playSplitCompletedSound, playScanErrorSound } from './audioUtils';
import ModalLaserBoxes from './terminal/ModalLaserBoxes';
import ModalLaserManual from './terminal/ModalLaserManual';
import ModalLaserSeal from './terminal/ModalLaserSeal';
import ModalLaserFastTrack from './terminal/ModalLaserFastTrack';
import ModalLaserReturn from './terminal/ModalLaserReturn';
import ModalLaserCameraScanner from './terminal/ModalLaserCameraScanner';
import ModalWarehouseEventsLedger from './ModalWarehouseEventsLedger';

import LaserStationHeader from './terminal/LaserStationHeader';
import LaserStationModeBar from './terminal/LaserStationModeBar';
import LaserStationScannerHUD from './terminal/LaserStationScannerHUD';
import LaserStationItemsList from './terminal/LaserStationItemsList';

export default function WarehouseLaserStation({ activeSplitId, onSplitFinished, onBackToQueue }) {
  const { user } = useAuth();
  const { can, isAdmin } = usePermissions();
  const isAdminOrAuditor = isAdmin || can(PERMISSIONS.WAREHOUSE_AUDIT) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canSendToFilter2 = isAdmin || can(PERMISSIONS.WAREHOUSE_FILTER2_SEND) || can(PERMISSIONS.WAREHOUSE_MANAGE) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR);
  const canSealDirect = isAdmin || can(PERMISSIONS.WAREHOUSE_SEAL_DIRECT) || can(PERMISSIONS.WAREHOUSE_MANAGE) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR);
  const canModeDirect = isAdmin || can(PERMISSIONS.WAREHOUSE_MODE_DIRECT) || can(PERMISSIONS.WAREHOUSE_MANAGE) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR);
  const canModeContainers = isAdmin || can(PERMISSIONS.WAREHOUSE_MODE_CONTAINERS) || can(PERMISSIONS.WAREHOUSE_MANAGE) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR);
  const canChecker = isAdmin || can(PERMISSIONS.WAREHOUSE_CHECKER) || can(PERMISSIONS.WAREHOUSE_MANAGE) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR);
  const canFastTrack = isAdmin || can(PERMISSIONS.WAREHOUSE_SUPERVISOR) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const [split, setSplit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [barcodeInput, setBarcodeInput] = useState('');
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState(null);
  const [flashType, setFlashType] = useState(null); // 'success' | 'error' | 'conflict'
  const [copiedBarcode, setCopiedBarcode] = useState(null);
  const [lastActiveItemId, setLastActiveItemId] = useState(null);
  const [activeContainerQr, setActiveContainerQr] = useState('');
  const [showCameraModal, setShowCameraModal] = useState(false);

  // Modales secundarios de la terminal
  const [boxModalItem, setBoxModalItem] = useState(null);
  const [boxesCount, setBoxesCount] = useState('1');
  const [unitsPerBox, setUnitsPerBox] = useState('10');
  const [manualModalItem, setManualModalItem] = useState(null);
  const [manualQty, setManualQty] = useState('1');
  const [manualReason, setManualReason] = useState('Rapidez operativa (flujo ágil)');
  const [customReason, setCustomReason] = useState('');
  const [showSealModal, setShowSealModal] = useState(false);
  const [sealMode, setSealMode] = useState('auto'); // 'auto' | 'physical' | 'none'
  const [sealFolio, setSealFolio] = useState('');

  // Errores en línea de modales
  const [boxModalError, setBoxModalError] = useState(null);
  const [manualModalError, setManualModalError] = useState(null);

  // Modales interactivos para Segundo Filtro (Revisión y Control de Calidad)
  const [showSegundoFiltroConfirmModal, setShowSegundoFiltroConfirmModal] = useState(false);
  const [segundoFiltroSuccessModal, setSegundoFiltroSuccessModal] = useState(false);
  const [sendingTo2doFiltro, setSendingTo2doFiltro] = useState(false);
  const [copiedSplitId, setCopiedSplitId] = useState(false);
  const [showEventsLedger, setShowEventsLedger] = useState(false);
  const [showBindContainerModal, setShowBindContainerModal] = useState(false);
  const [containerQrInput, setContainerQrInput] = useState('');
  const [bindingContainer, setBindingContainer] = useState(false);
  const [bindContainerError, setBindContainerError] = useState(null);

  const handleCopySplitId = (e) => {
    e?.stopPropagation();
    if (!split) return;
    const idToCopy = `${split.order_id}-${split.split_number ?? split.split_index ?? 1}`;
    try {
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(idToCopy).catch(() => {});
      }
    } catch {}
    setCopiedSplitId(true);
    setTimeout(() => setCopiedSplitId(false), 3000);
  };

  // Estados de Fast-Track (Confiar en Surtido) y Devolución por Discrepancia
  const [showFastTrackModal, setShowFastTrackModal] = useState(false);
  const [fastTracking, setFastTracking] = useState(false);
  const [showReturnSurtidoModal, setShowReturnSurtidoModal] = useState(false);
  const [returningToSurtido, setReturningToSurtido] = useState(false);

  const barcodeInputRef = useRef(null);

  // Detección de dispositivos táctiles (Celulares y Tablets vs PC / Laptop de escritorio)
  const isTouchDeviceOrTablet = () => {
    if (typeof window === 'undefined') return false;
    // Ancho <= 1024px cubre celulares y tablets (iPad vertical/horizontal, Galaxy Tab)
    // O dispositivos con capacidades touch activas hasta 1280px (iPad Pro)
    const isTabletOrMobileWidth = window.innerWidth <= 1024;
    const hasTouchScreen = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
    return isTabletOrMobileWidth || (hasTouchScreen && window.innerWidth <= 1280);
  };

  // Mantener auto-focus permanente en la entrada del escáner láser (solo en PC/Laptop con lector físico; en Celular y Tablet NO forzar foco para no desplegar teclado virtual)
  useEffect(() => {
    if (isTouchDeviceOrTablet()) return;

    if (!boxModalItem && !manualModalItem && !showSealModal && !showFastTrackModal && !showReturnSurtidoModal) {
      const focusTimer = setTimeout(() => {
        barcodeInputRef.current?.focus();
      }, 100);
      return () => clearTimeout(focusTimer);
    }
  }, [boxModalItem, manualModalItem, showSealModal, showFastTrackModal, showReturnSurtidoModal, split]);

  const [claiming, setClaiming] = useState(false);

  useEffect(() => {
    if (activeSplitId) {
      loadSplit();
    }
  }, [activeSplitId]);

  const loadSplit = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await warehouseService.getSplitByCode(activeSplitId);
      setSplit(data);
      const cqr = data?.active_container_qr || data?.container_qr || (data?.containers?.length > 0 ? data.containers[data.containers.length - 1].qr_code : '');
      if (cqr) {
        setActiveContainerQr(cqr);
      }
    } catch (err) {
      setError(err.detail || err.message || 'Error al cargar split');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (split) {
      const cqr = split.active_container_qr || split.container_qr || (split.containers?.length > 0 ? split.containers[split.containers.length - 1].qr_code : '');
      if (cqr && !activeContainerQr) {
        setActiveContainerQr(cqr);
      }
    }
  }, [split]);

  const handleClaimSplitInStation = async () => {
    try {
      setClaiming(true);
      setError(null);
      const isChecking = split?.status === 'ready_for_check' || split?.status === 'checking';
      await warehouseService.claimSplit(activeSplitId, isChecking ? 'checker' : 'picker');
      await loadSplit();
    } catch (err) {
      setError(err.detail || err.message || 'No se pudo auto-asignar el split');
    } finally {
      setClaiming(false);
    }
  };

  // Escaneo Unificado: ejecuta la llamada al backend con vibración háptica y sin desplegar teclado en móvil
  const executeScan = async (code) => {
    const cleanCode = (code || '').trim();
    if (!cleanCode || cleanCode === 'Sin código' || scanning || split.status === 'completed') return;

    // Vibración háptica en móvil para feedback instantáneo similar a pistola física
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      try {
        navigator.vibrate(40);
      } catch {}
    }

    try {
      setScanning(true);
      setScanMessage(null);
      setCopiedBarcode(cleanCode);
      setTimeout(() => setCopiedBarcode(null), 1500);

      const effectiveContainer = activeContainerQr || split?.active_container_qr || split?.container_qr || null;
      const res = await warehouseService.scanBarcode(split.split_id, cleanCode, effectiveContainer);

      playScanSuccessSound();
      setFlashType('success');

      if (res.is_container || res.action === 'container_activated' || res.container_qr) {
        const cqr = res.container_qr || res.active_container_qr;
        if (cqr) {
          setActiveContainerQr(cqr);
          setSplit((prev) => prev ? ({ ...prev, active_container_qr: cqr, container_qr: cqr, uses_containers: true }) : prev);
        }
        setScanMessage({
          type: 'success',
          text: res.message || `🧺 Canasta activada: ${cqr}`
        });
      } else {
        if (res.order_item_id || res.product_id) {
          setLastActiveItemId(res.order_item_id || res.product_id);
        }
        const verifiedShow = res.is_checking_mode ? (res.checker_total_verified ?? 0) : (res.total_verified ?? 0);
        setScanMessage({
          type: 'success',
          text: res.message || `✓ Escaneado: ${res.product_name} (${verifiedShow}/${res.required_quantity ?? 0})`
        });
      }

      // Recargar split para actualizar conteos
      const updatedSplit = await warehouseService.getSplit(split.split_id);
      setSplit(updatedSplit);
      const updatedCqr = updatedSplit.active_container_qr || updatedSplit.container_qr;
      if (updatedCqr) {
        setActiveContainerQr(updatedCqr);
      }

      if (updatedSplit.is_complete) {
        playSplitCompletedSound();
      }
    } catch (err) {
      playScanErrorSound();
      const rawMsg = err.response?.data?.detail || err.detail || err.message || 'Error al procesar escaneo';
      const isConflict = typeof rawMsg === 'string' && rawMsg.toLowerCase().includes('otro split');
      setFlashType(isConflict ? 'conflict' : 'error');
      setScanMessage({
        type: isConflict ? 'conflict' : 'error',
        text: rawMsg
      });
    } finally {
      setBarcodeInput('');
      setScanning(false);
      setTimeout(() => setFlashType(null), 800);

      // En celulares y tablets NUNCA robar foco al input para que no salte el teclado virtual en pantalla
      // En PC/Laptop de escritorio sí mantener foco para lectores láser USB físicos
      if (!isTouchDeviceOrTablet()) {
        barcodeInputRef.current?.focus();
      } else {
        barcodeInputRef.current?.blur();
      }
    }
  };

  const handleScanSubmit = async (e) => {
    e?.preventDefault();
    const code = barcodeInput.trim();
    if (!code) return;
    await executeScan(code);
  };

  // Disparo de escaneo directo (1-Tap Scan para móvil sin teclado)
  const handleDirectScan = async (code, e, item = null) => {
    e?.stopPropagation();
    if (!code || code === 'Sin código') return;
    if (item) {
      setLastActiveItemId(item.order_item_id || item.product_id);
    }
    await executeScan(code);
  };

  // Empaque por Cajas Maestras
  const handleAddBoxes = async (e) => {
    e.preventDefault();
    if (!boxModalItem) return;

    setBoxModalError(null);
    const effectiveContainer = activeContainerQr || split?.active_container_qr || split?.container_qr;
    if (split?.uses_containers && !effectiveContainer) {
      setBoxModalError('🧺 Modo Canastas activo: Debes escanear o vincular el código QR de una canasta física antes de empaquetar cajas.');
      playScanErrorSound();
      return;
    }

    const count = parseInt(boxesCount, 10);
    const units = parseInt(unitsPerBox, 10);
    if (isNaN(count) || count < 1 || isNaN(units) || units < 1) {
      setBoxModalError('El número de cajas y unidades por caja deben ser números válidos mayores a cero');
      playScanErrorSound();
      return;
    }

    const isChecking = split?.status === 'ready_for_check' || split?.status === 'checking';
    const req = boxModalItem.quantity ?? boxModalItem.quantity_required ?? 0;
    
    const prevBoxes = isChecking ? (boxModalItem.checker_boxes || 0) : (boxModalItem.boxes || 0);
    const prevBoxProds = isChecking ? (boxModalItem.checker_box_prods || 0) : (boxModalItem.box_prods || 0);
    const prevUnits = (prevBoxes > 0 && prevBoxProds > 0) ? Math.round(prevBoxProds / prevBoxes) : 0;
    const isChangingUnitSize = prevUnits > 0 && units > 0 && units !== prevUnits;

    const otherVerified = isChecking
      ? ((boxModalItem.checker_scanned_prods || 0) + (boxModalItem.checker_manual_prods || 0))
      : ((boxModalItem.scanned_prods || 0) + (boxModalItem.manual_prods || 0));

    const available = Math.max(0, req - otherVerified - (isChangingUnitSize ? 0 : prevBoxProds));
    const totalToAdd = count * units;

    if (totalToAdd > available) {
      setBoxModalError(`Exceso de producto: Se intentan registrar ${totalToAdd} piezas (${count} cajas x ${units} pzas), pero solo caben ${available} piezas para completar los requerimientos de esta partida (${req} requeridos, ${otherVerified} por láser/manual).`);
      playScanErrorSound();
      return;
    }

    try {
      setLoading(true);
      setLastActiveItemId(boxModalItem.order_item_id || boxModalItem.product_id);
      await warehouseService.addBoxes(split.split_id, boxModalItem.order_item_id, count, units, effectiveContainer);
      playScanSuccessSound();
      
      setBoxModalItem(null);
      setBoxModalError(null);
      const updated = await warehouseService.getSplit(split.split_id);
      setSplit(updated);
    } catch (err) {
      playScanErrorSound();
      setBoxModalError(err.detail || err.message || 'Error al registrar cajas');
    } finally {
      setLoading(false);
    }
  };

  // Validación Manual Justificada
  const handleAddManual = async (e) => {
    e.preventDefault();
    if (!manualModalItem) return;

    setManualModalError(null);
    const effectiveContainer = activeContainerQr || split?.active_container_qr || split?.container_qr;
    if (split?.uses_containers && !effectiveContainer) {
      setManualModalError('🧺 Modo Canastas activo: Debes escanear o vincular el código QR de una canasta física antes de registrar validación manual.');
      playScanErrorSound();
      return;
    }

    const qty = parseInt(manualQty, 10);
    if (isNaN(qty) || qty < 1) {
      setManualModalError('La cantidad a validar manualmente debe ser de al menos 1 pieza');
      playScanErrorSound();
      return;
    }

    const isChecking = split?.status === 'ready_for_check' || split?.status === 'checking';
    const requiredQty = manualModalItem.quantity ?? manualModalItem.quantity_required ?? 0;
    const currentVerified = isChecking ? (manualModalItem.checker_total_verified || 0) : (manualModalItem.total_verified || 0);
    const remainingQty = Math.max(0, requiredQty - currentVerified);

    if (qty > remainingQty) {
      setManualModalError(`No puedes registrar ${qty} piezas. Solo faltan ${remainingQty} piezas por ${isChecking ? 'revisar' : 'completar'} en esta partida.`);
      playScanErrorSound();
      return;
    }

    const reason = manualReason === 'Otro' ? customReason : manualReason;
    if (!reason || !reason.trim()) {
      setManualModalError('Debes indicar el motivo de la validación manual');
      playScanErrorSound();
      return;
    }

    try {
      setLoading(true);
      setLastActiveItemId(manualModalItem.order_item_id || manualModalItem.product_id);
      await warehouseService.addManual(split.split_id, manualModalItem.order_item_id, qty, reason.trim(), effectiveContainer);
      playScanSuccessSound();
      setManualModalItem(null);
      setManualModalError(null);
      setCustomReason('');
      const updated = await warehouseService.getSplit(split.split_id);
      setSplit(updated);
    } catch (err) {
      playScanErrorSound();
      setManualModalError(err.detail || err.message || 'Error al registrar validación manual');
    } finally {
      setLoading(false);
    }
  };

  // Cierre y Precintado Inviolable
  const handleSealSplit = async (e) => {
    e.preventDefault();
    let finalFolio = null;

    if (sealMode === 'none') {
      finalFolio = 'Sin sello';
    } else {
      if (!sealFolio || !sealFolio.trim()) {
        alert('Debes ingresar o generar un folio de seguridad para sellar el split');
        return;
      }
      finalFolio = sealFolio.trim();
    }

    try {
      setLoading(true);
      await warehouseService.advanceSplitStatus(split.split_id, {
        security_seal_folio: finalFolio,
        new_status: 'completed'
      });
      playSplitCompletedSound();
      setShowSealModal(false);
      if (onSplitFinished) onSplitFinished(split.split_id);
    } catch (err) {
      playScanErrorSound();
      alert(err.message || 'Error al sellar split');
    } finally {
      setLoading(false);
    }
  };

  // Enviar a Segundo Filtro Opcional (Mesa de Revisión / Checking)
  const handleSendToSegundoFiltro = () => {
    setShowSegundoFiltroConfirmModal(true);
  };

  const confirmSendToSegundoFiltro = async () => {
    try {
      setSendingTo2doFiltro(true);
      await warehouseService.advanceSplitStatus(split.split_id, {
        new_status: 'ready_for_check'
      });
      playScanSuccessSound();
      setShowSegundoFiltroConfirmModal(false);
      setSegundoFiltroSuccessModal(true);
    } catch (err) {
      playScanErrorSound();
      alert(err.detail || err.message || 'Error al enviar a segundo filtro');
    } finally {
      setSendingTo2doFiltro(false);
    }
  };

  // Regresar a Surtido por Discrepancia física detectada en segundo filtro
  const handleReturnToSurtido = () => {
    setShowReturnSurtidoModal(true);
  };

  const confirmReturnToSurtido = async () => {
    try {
      setReturningToSurtido(true);
      await warehouseService.advanceSplitStatus(split.split_id, {
        new_status: 'in_progress'
      });
      playScanErrorSound();
      setShowReturnSurtidoModal(false);
      alert('↩️ Split devuelta a piso de surtido por discrepancia física exitosamente.');
      if (onSplitFinished) {
        onSplitFinished(split.split_id);
      } else if (onBackToQueue) {
        onBackToQueue();
      }
    } catch (err) {
      playScanErrorSound();
      alert(err.detail || err.message || 'Error al regresar split a surtido');
    } finally {
      setReturningToSurtido(false);
    }
  };

  // Validar Todo por Confianza (Fast-Track) en Segundo Filtro
  const handleConfirmFastTrack = async () => {
    try {
      setFastTracking(true);
      await warehouseService.checkerFastTrack(split.split_id);
      playScanSuccessSound();
      setShowFastTrackModal(false);
      setScanMessage({
        type: 'success',
        text: `🤝 Se validaron todas las partidas confiando en el surtido previo de ${split.picker_name || 'piso'}.`
      });
      const updated = await warehouseService.getSplit(split.split_id);
      setSplit(updated);
    } catch (err) {
      playScanErrorSound();
      alert(err.detail || err.message || 'Error al validar por confianza');
    } finally {
      setFastTracking(false);
    }
  };

  // Vincular Canasta QR a Split
  const handleBindContainer = async (e) => {
    e?.preventDefault();
    const qr = containerQrInput.trim().toUpperCase();
    if (!qr || !split) return;

    try {
      setBindingContainer(true);
      setBindContainerError(null);
      await warehouseService.bindContainerToSplit(split.split_id, qr);
      playScanSuccessSound();
      setShowBindContainerModal(false);
      setContainerQrInput('');
      setActiveContainerQr(qr);
      const updated = await warehouseService.getSplit(split.split_id);
      setSplit(updated);
      setScanMessage({ type: 'success', text: `✓ Canasta QR vinculada y activa: ${qr}` });
    } catch (err) {
      playScanErrorSound();
      setBindContainerError(err.response?.data?.detail || err.message || 'Error al vincular canasta QR');
    } finally {
      setBindingContainer(false);
    }
  };

  // Liberar Canasta QR de Split con confirmación interactiva de vaciado
  const handleReleaseContainer = async (containerId, qrCode, forceEmpty = false) => {
    const cId = containerId || split?.active_container_id || split?.container_id;
    if (!split || !cId) return;

    const targetContainer = (split.containers || []).find(c => c.container_id === cId);
    const targetSummary = (split.containers_summary || []).find(s => s.container_id === cId);
    const targetQr = qrCode || targetContainer?.qr_code || targetSummary?.qr_code || 'seleccionada';
    const totalPieces = targetSummary?.total_pieces ?? 0;

    let emptyItems = Boolean(forceEmpty);
    if (!emptyItems && totalPieces > 0) {
      const confirmMsg = `⚠️ ATENCIÓN: La canasta '${targetQr}' contiene ${totalPieces} pieza(s) depositada(s) en este lote.\n\nPara desvincularla, es necesario vaciarla y regresar las piezas al estatus 'pendiente' para que puedan ser surtidas nuevamente.\n\n👉 ¿Deseas CONFIRMAR el vaciado de las piezas y desvincular la canasta ahora?`;
      if (!window.confirm(confirmMsg)) {
        return;
      }
      emptyItems = true;
    }

    try {
      setLoading(true);
      await warehouseService.releaseContainer({ container_id: cId, empty_items: emptyItems });
      playScanSuccessSound();
      const updated = await warehouseService.getSplit(split.split_id);
      setSplit(updated);
      const newActive = updated.active_container_qr || updated.container_qr || (updated.containers?.length > 0 ? updated.containers[updated.containers.length - 1].qr_code : '');
      setActiveContainerQr(newActive);
      setScanMessage({
        type: 'success',
        text: emptyItems
          ? `✓ Canasta '${targetQr}' vaciada y liberada. Las piezas regresaron a pendientes.`
          : `✓ Canasta '${targetQr}' liberada del split.`
      });
    } catch (err) {
      playScanErrorSound();
      const errorDetail = err.response?.data?.detail || err.message || 'Error al liberar canasta';

      // Si el backend solicita confirmación de vaciado porque hay piezas adentro
      if (errorDetail.includes('Confirma el vaciado') || errorDetail.includes('pieza(s) depositada(s)')) {
        const wantsEmpty = window.confirm(
          `⚠️ ${errorDetail}\n\n👉 ¿Deseas CONFIRMAR el vaciado de las piezas para devolverlas a 'pendientes' y desvincular la canasta ahora mismo?`
        );
        if (wantsEmpty) {
          return handleReleaseContainer(cId, targetQr, true);
        }
      } else {
        alert(errorDetail);
      }
    } finally {
      setLoading(false);
    }
  };

  // Alternar / Cambiar canasta activa
  const handleSwitchContainer = async (qr) => {
    if (!qr || !split) return;
    try {
      setLoading(true);
      await warehouseService.activateContainer(split.split_id, qr);
      playScanSuccessSound();
      setActiveContainerQr(qr);
      const updated = await warehouseService.getSplit(split.split_id);
      setSplit(updated);
      setScanMessage({ type: 'success', text: `🧺 Canasta activa cambiada a: ${qr}` });
    } catch (err) {
      playScanErrorSound();
      alert(err.response?.data?.detail || err.message || 'Error al cambiar de canasta');
    } finally {
      setLoading(false);
    }
  };

  // Alternar modalidad de canastas vs surtido directo
  const [togglingContainerMode, setTogglingContainerMode] = useState(false);
  const [showResetModeModal, setShowResetModeModal] = useState(false);
  const [resetModeUnits, setResetModeUnits] = useState(0);

  const handleToggleContainerMode = async (enableContainers, resetProgress = false) => {
    if (!split) return;

    // Si intenta pasar a Canastas y ya tiene piezas verificadas y no ha confirmado reset
    if (enableContainers && !split.uses_containers && !resetProgress) {
      const verified = split.items?.reduce((acc, it) => acc + (it.total_verified ?? 0), 0) || 0;
      if (verified > 0) {
        setResetModeUnits(verified);
        setShowResetModeModal(true);
        return;
      }
    }

    // Si intenta pasar de Canastas a Surtido Directo, pedir confirmación amistosa
    if (!enableContainers && split.uses_containers) {
      if (!window.confirm("¿Deseas desvincular las canastas físicas y pasar a Surtido Directo por Split?\n\nLas canastas quedarán liberadas y el progreso de piezas surtidas se mantendrá intacto.")) {
        return;
      }
    }

    try {
      setTogglingContainerMode(true);
      await warehouseService.setContainerMode(split.split_id, enableContainers, resetProgress);
      playScanSuccessSound();
      const updated = await warehouseService.getSplit(split.split_id);
      setSplit(updated);
      setShowResetModeModal(false);
      if (enableContainers) {
        setScanMessage({
          type: 'success',
          text: resetProgress
            ? '🧺 Modo Canastas activado. El avance previo se reinició a 0 para auditoría de canasta.'
            : '🧺 Modo canastas activado. Escanea o vincula tu primer canasta QR.'
        });
        setShowBindContainerModal(true);
      } else {
        setScanMessage({ type: 'success', text: '📦 Modo Surtido Directo (Sin Canastas) activado. Canastas liberadas.' });
      }
    } catch (err) {
      playScanErrorSound();
      if (err.response?.status === 409) {
        const units = err.response.data?.picked_units || split.items?.reduce((acc, it) => acc + (it.total_verified ?? 0), 0) || 0;
        setResetModeUnits(units);
        setShowResetModeModal(true);
        return;
      }
      alert(err.response?.data?.detail || err.message || 'Error al cambiar modalidad');
    } finally {
      setTogglingContainerMode(false);
    }
  };

  // Calcular porcentaje completado de el split (antes de early returns para respetar Rules of Hooks)
  const isSegundoFiltro = split?.status === 'ready_for_check' || split?.status === 'checking';
  const totalRequired = split?.items?.reduce((acc, it) => acc + (it.quantity ?? it.quantity_required ?? 0), 0) || 0;
  const totalVerified = split?.items?.reduce((acc, it) => acc + (it.total_verified ?? 0), 0) || 0;
  const checkerTotalVerified = split?.items?.reduce((acc, it) => acc + (it.checker_total_verified ?? 0), 0) || 0;

  const currentProgressCount = isSegundoFiltro ? checkerTotalVerified : totalVerified;
  const progressPct = totalRequired > 0 ? Math.min(100, Math.round((currentProgressCount / totalRequired) * 100)) : 0;
  const isAllVerified = totalRequired > 0 && Boolean(split?.items?.length) && split.items.every(it => (it.total_verified || 0) >= (it.quantity ?? it.quantity_required ?? 0));
  const isAllCheckerVerified = totalRequired > 0 && Boolean(split?.items?.length) && split.items.every(it => (it.checker_total_verified || 0) >= (it.quantity ?? it.quantity_required ?? 0));

  // Detección de discrepancias forenses en 2do filtro (Solo visible para Administradores / Auditores)
  const itemsWithDiscrepancy = (isSegundoFiltro && isAdminOrAuditor)
    ? (split?.items?.filter(it => it.has_forensic_discrepancy || ((it.checker_total_verified || 0) > 0 && (it.checker_total_verified || 0) !== (it.total_verified || 0))) || [])
    : [];
  const hasActiveDiscrepancy = itemsWithDiscrepancy.length > 0;

  // Ordenamiento determinista de partidas (Hook incondicional)
  const sortedItems = useMemo(() => {
    if (!split?.items || !Array.isArray(split.items)) return [];
    return [...split.items].sort((a, b) => {
      const reqA = a.quantity ?? a.quantity_required ?? 0;
      const reqB = b.quantity ?? b.quantity_required ?? 0;
      const verA = isSegundoFiltro ? (a.checker_total_verified || 0) : (a.total_verified || 0);
      const verB = isSegundoFiltro ? (b.checker_total_verified || 0) : (b.total_verified || 0);
      const doneA = verA >= reqA;
      const doneB = verB >= reqB;

      const idA = a.order_item_id || a.product_id;
      const idB = b.order_item_id || b.product_id;
      const isCurA = idA === lastActiveItemId;
      const isCurB = idB === lastActiveItemId;

      // El que se esté surtiendo actualmente va hasta arriba
      if (isCurA && !isCurB) return -1;
      if (!isCurA && isCurB) return 1;

      // Incompletos primero, completos al final
      if (!doneA && doneB) return -1;
      if (doneA && !doneB) return 1;

      // Ordenar por ubicación / anaquel
      const locA = (a.location || 'ZZZ').trim();
      const locB = (b.location || 'ZZZ').trim();
      const locCmp = locA.localeCompare(locB, undefined, { numeric: true });
      if (locCmp !== 0) return locCmp;

      // Desempate por nombre de producto
      const nameA = (a.product_name || '').trim();
      const nameB = (b.product_name || '').trim();
      return nameA.localeCompare(nameB);
    });
  }, [split?.items, lastActiveItemId, isSegundoFiltro]);

  if (loading && !split) {
    return <LoadingSpinner message="Inicializando terminal láser..." />;
  }

  if (error) {
    const isBlindForbidden = error.toLowerCase().includes('surtido ciego') ||
                             error.toLowerCase().includes('tomar el split');
    if (isBlindForbidden) {
      return (
        <div className="warehouse-claim-notice">
          <div className="warehouse-claim-notice__icon">🔒</div>
          <div className="warehouse-claim-notice__content">
            <h4>Surtido Ciego Activo</h4>
            <p className="mb-3">
              Este split está protegida bajo Surtido Ciego. Para desbloquearla y visualizar las partidas a recolectar, primero debes auto-asignártela.
            </p>
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn--primary"
                onClick={handleClaimSplitInStation}
                disabled={claiming}
              >
                {claiming ? 'Tomando split...' : '⚡ Tomar Split para Surtir'}
              </button>
              <button type="button" className="btn btn--secondary" onClick={onBackToQueue}>
                Volver a la Cola FIFO
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="alert alert--danger">
        <p>{error}</p>
        <button type="button" className="btn btn--secondary mt-2" onClick={onBackToQueue}>
          Volver a la Cola
        </button>
      </div>
    );
  }

  if (!split) return null;

  return (
    <div className="warehouse-terminal">
      {/* Encabezado y Acciones de Split / Filtros */}
      <LaserStationHeader
        split={split}
        isSegundoFiltro={isSegundoFiltro}
        hasActiveDiscrepancy={hasActiveDiscrepancy}
        itemsWithDiscrepancy={itemsWithDiscrepancy}
        onBackToQueue={onBackToQueue}
        setShowEventsLedger={setShowEventsLedger}
        isAllVerified={isAllVerified}
        canSendToFilter2={canSendToFilter2}
        canSealDirect={canSealDirect}
        canChecker={canChecker}
        canFastTrack={canFastTrack}
        handleSendToSegundoFiltro={handleSendToSegundoFiltro}
        loading={loading}
        setSealMode={setSealMode}
        setSealFolio={setSealFolio}
        setShowSealModal={setShowSealModal}
        handleReturnToSurtido={handleReturnToSurtido}
        setShowFastTrackModal={setShowFastTrackModal}
        fastTracking={fastTracking}
        isAllCheckerVerified={isAllCheckerVerified}
      />

      {/* Barra de Modalidad Operativa y Canastas QR */}
      <LaserStationModeBar
        split={split}
        isSegundoFiltro={isSegundoFiltro}
        canModeContainers={canModeContainers}
        canModeDirect={canModeDirect}
        handleSwitchContainer={handleSwitchContainer}
        handleReleaseContainer={handleReleaseContainer}
        handleToggleContainerMode={handleToggleContainerMode}
        togglingContainerMode={togglingContainerMode}
        setBindContainerError={setBindContainerError}
        setContainerQrInput={setContainerQrInput}
        setShowBindContainerModal={setShowBindContainerModal}
      />

      {/* HUD del Escáner Láser, Guía y Progreso */}
      <LaserStationScannerHUD
        split={split}
        isSegundoFiltro={isSegundoFiltro}
        isAdminOrAuditor={isAdminOrAuditor}
        flashType={flashType}
        barcodeInputRef={barcodeInputRef}
        barcodeInput={barcodeInput}
        setBarcodeInput={setBarcodeInput}
        scanning={scanning}
        handleScanSubmit={handleScanSubmit}
        executeScan={executeScan}
        setShowCameraModal={setShowCameraModal}
        scanMessage={scanMessage}
        currentProgressCount={currentProgressCount}
        totalRequired={totalRequired}
        progressPct={progressPct}
        totalVerified={totalVerified}
        checkerTotalVerified={checkerTotalVerified}
      />

      {/* Listado de Partidas a Surtir (Ordenadas por Anaquel/Ubicación) */}
      <LaserStationItemsList
        sortedItems={sortedItems}
        split={split}
        isSegundoFiltro={isSegundoFiltro}
        isAdminOrAuditor={isAdminOrAuditor}
        lastActiveItemId={lastActiveItemId}
        copiedBarcode={copiedBarcode}
        setCopiedBarcode={setCopiedBarcode}
        handleDirectScan={handleDirectScan}
        scanning={scanning}
        setBoxModalItem={setBoxModalItem}
        setBoxesCount={setBoxesCount}
        setUnitsPerBox={setUnitsPerBox}
        setBoxModalError={setBoxModalError}
        setManualModalItem={setManualModalItem}
        setManualQty={setManualQty}
        setManualReason={setManualReason}
        setCustomReason={setCustomReason}
        setManualModalError={setManualModalError}
      />

      {/* Modales Extraídos de la Terminal */}
      <ModalLaserBoxes
        item={boxModalItem}
        isSegundoFiltro={isSegundoFiltro}
        boxesCount={boxesCount}
        setBoxesCount={setBoxesCount}
        unitsPerBox={unitsPerBox}
        setUnitsPerBox={setUnitsPerBox}
        boxModalError={boxModalError}
        setBoxModalError={setBoxModalError}
        onClose={() => setBoxModalItem(null)}
        onSubmit={handleAddBoxes}
        loading={loading}
      />

      <ModalLaserManual
        item={manualModalItem}
        isSegundoFiltro={isSegundoFiltro}
        manualQty={manualQty}
        setManualQty={setManualQty}
        manualReason={manualReason}
        setManualReason={setManualReason}
        customReason={customReason}
        setCustomReason={setCustomReason}
        manualModalError={manualModalError}
        onClose={() => setManualModalItem(null)}
        onSubmit={handleAddManual}
        loading={loading}
      />

      <ModalLaserSeal
        isOpen={showSealModal}
        onClose={() => setShowSealModal(false)}
        split={split}
        hasActiveDiscrepancy={hasActiveDiscrepancy}
        itemsWithDiscrepancy={itemsWithDiscrepancy}
        sealMode={sealMode}
        setSealMode={setSealMode}
        sealFolio={sealFolio}
        setSealFolio={setSealFolio}
        onSubmit={handleSealSplit}
        loading={loading}
      />

      <ModalLaserFastTrack
        isOpen={showFastTrackModal}
        onClose={() => setShowFastTrackModal(false)}
        split={split}
        totalRequired={totalRequired}
        onConfirm={handleConfirmFastTrack}
        loading={fastTracking}
      />

      <ModalLaserReturn
        isOpen={showReturnSurtidoModal}
        onClose={() => setShowReturnSurtidoModal(false)}
        split={split}
        onConfirm={confirmReturnToSurtido}
        loading={returningToSurtido}
      />

      {/* Modal Confirmación de Envío a Segundo Filtro */}
      {showSegundoFiltroConfirmModal && (
        <div className="modal-overlay" onClick={() => setShowSegundoFiltroConfirmModal(false)}>
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="d-flex align-items-center gap-2 m-0 text-base">
                <span>🔍</span> Enviar a Segundo Filtro
              </h3>
              <button type="button" className="modal__close" onClick={() => setShowSegundoFiltroConfirmModal(false)}>&times;</button>
            </div>
            <div className="modal__body">
              <p className="text-sm mb-3">
                Has completado la recolección física al 100% de la <strong>Split #{split.split_number ?? 1}</strong> (Pedido #{split.order_id}).
              </p>

              {/* Tarjeta de Identificador Pedido-Split para Rotulado y Búsqueda en 2do Filtro */}
              <div className="p-3 mb-3 bg-light rounded border text-center">
                <span className="text-xs text-muted d-block mb-1 font-semibold">
                  🏷️ Identificador de Split / Canasta (para rotular o buscar):
                </span>
                <div className="d-flex align-items-center justify-content-center gap-2 my-1">
                  <span className="font-mono text-xl font-bold text-primary px-3 py-1 bg-white rounded border">
                    {split.order_id}-{split.split_number ?? split.split_index ?? 1}
                  </span>
                  <button
                    type="button"
                    className={`btn btn--sm ${copiedSplitId ? 'btn--success' : 'btn--secondary'} font-bold`}
                    onClick={handleCopySplitId}
                    title="Copiar identificador pedido-split"
                  >
                    {copiedSplitId ? '✓ ¡Copiado!' : '📋 Copiar ID'}
                  </button>
                </div>
                <span className="text-xs text-muted mt-1 d-block">
                  Escribe o pega este ID en la canasta física para que el Revisor lo localice al instante tecleando <strong>{split.order_id}-{split.split_number ?? split.split_index ?? 1}</strong> en su buscador.
                </span>
              </div>

              <div className="alert alert--info text-xs mb-3 leading-normal">
                <strong>ℹ️ Mesa de Calidad y Doble Verificación:</strong>
                <p className="m-0 mt-1">
                  El split pasará al estatus <em>"ready_for_check"</em> para que un revisor (checker) verifique físicamente los productos antes de autorizar el sellado final con cincho inviolable.
                </p>
              </div>
              <p className="text-xs text-muted m-0">
                ¿Deseas enviar este split a la mesa de segundo filtro ahora?
              </p>
            </div>
            <div className="modal__footer warehouse-terminal__modal-footer-responsive">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => setShowSegundoFiltroConfirmModal(false)}
                disabled={sendingTo2doFiltro}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn--primary font-bold"
                onClick={confirmSendToSegundoFiltro}
                disabled={sendingTo2doFiltro}
              >
                {sendingTo2doFiltro ? 'Transfiriendo...' : 'Confirmar Envío al 2do Filtro'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Éxito de Transferencia a Segundo Filtro */}
      {segundoFiltroSuccessModal && (
        <div className="modal-overlay">
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="d-flex align-items-center gap-2 m-0 text-base text-success font-bold">
                <span>✓</span> Split en Segundo Filtro
              </h3>
            </div>
            <div className="modal__body text-center py-4">
              <div className="text-4xl mb-2">🔍</div>
              <h4 className="mb-2">¡Split #{split.split_number ?? 1} transferida con éxito!</h4>

              {/* Tarjeta de Identificador con botón copiar */}
              <div className="p-3 my-3 bg-light rounded border text-center">
                <span className="text-xs text-muted d-block mb-1 font-semibold">
                  🏷️ Identificador de Split / Canasta:
                </span>
                <div className="d-flex align-items-center justify-content-center gap-2 my-1">
                  <span className="font-mono text-2xl font-bold text-primary px-3 py-1 bg-white rounded border">
                    {split.order_id}-{split.split_number ?? split.split_index ?? 1}
                  </span>
                  <button
                    type="button"
                    className={`btn btn--sm ${copiedSplitId ? 'btn--success' : 'btn--secondary'} font-bold`}
                    onClick={handleCopySplitId}
                    title="Copiar ID para rotular o buscar"
                  >
                    {copiedSplitId ? '✓ ¡Copiado!' : '📋 Copiar ID'}
                  </button>
                </div>
                <span className="text-xs text-muted mt-2 d-block">
                  Rotula este código en la canasta física. El revisor podrá localizarlo de inmediato buscando <strong>{split.order_id}-{split.split_number ?? split.split_index ?? 1}</strong> en la cola.
                </span>
              </div>

              <p className="text-xs text-muted mb-0">
                Tu labor de recolección en piso ha concluido. El split quedó en espera en la Mesa de Revisión y Calidad.
              </p>
            </div>
            <div className="modal__footer d-flex flex-column gap-2">
              <button
                type="button"
                className="btn btn--primary w-100 font-bold"
                onClick={() => {
                  setSegundoFiltroSuccessModal(false);
                  if (onSplitFinished) onSplitFinished(split.split_id);
                  else if (onBackToQueue) onBackToQueue();
                }}
              >
                📋 Volver a Cola FIFO (Siguiente Pedido)
              </button>
              <button
                type="button"
                className="btn btn--secondary w-100"
                onClick={async () => {
                  try {
                    setLoading(true);
                    setSegundoFiltroSuccessModal(false);
                    await warehouseService.claimSplit(split.split_id, 'checker');
                    const updated = await warehouseService.getSplit(split.split_id);
                    setSplit(updated);
                  } catch (err) {
                    console.error('Error autoasignando checker:', err);
                    const updated = await warehouseService.getSplit(split.split_id);
                    setSplit(updated);
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                🔍 Auditar ahora en esta terminal (Como Revisor)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Bitácora Atómica de Escaneos (Event Ledger) */}
      {showEventsLedger && split && (
        <ModalWarehouseEventsLedger
          isOpen={showEventsLedger}
          onClose={() => setShowEventsLedger(false)}
          splitId={split.split_id}
          splitCode={split.split_code}
          orderId={split.order_id}
          split={split}
        />
      )}

      {/* Modal: Confirmación de Reinicio al activar Canastas QR */}
      {showResetModeModal && (
        <div className="modal-overlay" onClick={() => setShowResetModeModal(false)}>
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3>⚠️ Reinicio de Surtido Requerido</h3>
              <button className="modal__close" onClick={() => setShowResetModeModal(false)}>&times;</button>
            </div>
            <div className="modal__body">
              <div className="alert alert--warning mb-3">
                <strong>🧺 Modo Canastas Estricto</strong>
                <p className="m-0 mt-1 text-xs">
                  Este lote tiene <strong>{resetModeUnits}</strong> pieza(s) recolectada(s) en <strong>Surtido Directo</strong>.
                </p>
              </div>
              <p className="text-sm text-secondary mb-3">
                Para auditar la trazabilidad física por canasta QR, la política de almacén exige que cada producto sea escaneado y depositado directamente en su contenedor.
              </p>
              <div className="p-3 bg-light rounded text-xs border">
                <strong>¿Confirmas reiniciar el conteo a 0?</strong>
                <p className="m-0 text-muted mt-1">
                  Se restablecerán a cero las piezas surtidas para permitir el escaneo individual dentro de canastas físicas.
                </p>
              </div>
            </div>
            <div className="modal__footer d-flex gap-2 justify-content-end">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => setShowResetModeModal(false)}
                disabled={togglingContainerMode}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn--danger font-bold"
                onClick={() => handleToggleContainerMode(true, true)}
                disabled={togglingContainerMode}
              >
                {togglingContainerMode ? 'Reiniciando...' : 'Reiniciar a 0 y Usar Canastas'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Vincular Canasta QR Física a Split */}
      {showBindContainerModal && (
        <div className="modal-overlay" onClick={() => setShowBindContainerModal(false)}>
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3>🧺 Vincular Canasta QR a Split</h3>
              <button className="modal__close" onClick={() => setShowBindContainerModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleBindContainer}>
              <div className="modal__body">
                {bindContainerError && <div className="alert alert--danger mb-2">{bindContainerError}</div>}
                <div className="form-group mb-2">
                  <label className="form-label">Código QR de la Canasta (Tote) *</label>
                  <input
                    type="text"
                    className="input font-mono"
                    placeholder="Escanea con la pistola o escribe (ej: TOTE-001)"
                    value={containerQrInput}
                    onChange={(e) => setContainerQrInput(e.target.value.toUpperCase())}
                    autoFocus
                    required
                  />
                  <small className="form-text text-muted">
                    Apunta la pistola láser al código QR adherido a la canasta física para vincularla a este pedido.
                  </small>
                </div>
              </div>
              <div className="modal__footer">
                <button type="button" className="btn btn--secondary" onClick={() => setShowBindContainerModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn--primary" disabled={bindingContainer || !containerQrInput.trim()}>
                  {bindingContainer ? 'Vinculando...' : 'Vincular Canasta'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Escaneo con Cámara (QR de canastas o código de barras de productos) */}
      <ModalLaserCameraScanner
        isOpen={showCameraModal}
        onClose={() => setShowCameraModal(false)}
        onScan={async (code) => {
          await executeScan(code);
        }}
        activeContainerQr={activeContainerQr || split.active_container_qr || split.container_qr}
        usesContainers={split.uses_containers}
        isSegundoFiltro={isSegundoFiltro}
      />
    </div>
  );
}
