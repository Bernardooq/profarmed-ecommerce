import { useState, useEffect } from 'react';
import promoAdService from '../services/promoAdService';

let cachedHasAds = null;
let pendingPromise = null;

/**
 * Invalida la caché en memoria para reflejar cambios tras editar publicidad en el panel admin.
 */
export function invalidatePromoAdsCache() {
  cachedHasAds = null;
  pendingPromise = null;
}

/**
 * Hook ligero que determina si existen secciones de publicidad activas para clientes.
 * Comparte una sola petición en vuelo para Header, SearchBar y SidebarDrawer.
 */
export default function useHasPromoAds(enabled = false) {
  const [hasAds, setHasAds] = useState(Boolean(cachedHasAds));

  useEffect(() => {
    if (!enabled) {
      setHasAds(false);
      return undefined;
    }

    if (cachedHasAds !== null) {
      setHasAds(cachedHasAds);
      return undefined;
    }

    let mounted = true;
    if (!pendingPromise) {
      pendingPromise = promoAdService
        .getActiveAds()
        .then((res) => Boolean(res?.has_ads && Array.isArray(res.sections) && res.sections.length > 0))
        .catch(() => false)
        .finally(() => {
          pendingPromise = null;
        });
    }

    pendingPromise.then((result) => {
      cachedHasAds = result;
      if (mounted) {
        setHasAds(result);
      }
    });

    return () => {
      mounted = false;
    };
  }, [enabled]);

  return hasAds;
}
