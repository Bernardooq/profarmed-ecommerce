import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

const STORAGE_KEY = 'fc_sidebar_visible';

export function useSidebar() {
  const auth = useAuth();
  const isAuthenticated = Boolean(auth?.isAuthenticated || (typeof window !== 'undefined' && localStorage.getItem('token')));

  const [isSidebarOpen, setIsSidebarOpenState] = useState(() => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      if (!token) return false;
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved !== null) {
        return saved === 'true';
      }
    } catch (e) {
      console.warn('Error reading sidebar preference:', e);
    }
    return typeof window !== 'undefined' && window.innerWidth >= 1024;
  });

  // Escuchar cambios para mantener sincronía entre Header, Header2 y SearchBar
  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === STORAGE_KEY && e.newValue !== null) {
        setIsSidebarOpenState(e.newValue === 'true');
      }
    };

    const handleCustomSync = (e) => {
      if (typeof e.detail === 'boolean') {
        setIsSidebarOpenState(prev => (prev !== e.detail ? e.detail : prev));
      }
    };

    window.addEventListener('storage', handleStorage);
    window.addEventListener('fc_sidebar_sync', handleCustomSync);

    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener('fc_sidebar_sync', handleCustomSync);
    };
  }, []);

  // Gestionar clase en body para diseño fijo en escritorio
  useEffect(() => {
    const handleResize = () => {
      if (!isAuthenticated || window.innerWidth < 1024) {
        document.body.classList.remove('sidebar-open-desktop');
      } else if (isSidebarOpen) {
        document.body.classList.add('sidebar-open-desktop');
      }
    };

    if (isAuthenticated && typeof window !== 'undefined' && window.innerWidth >= 1024 && isSidebarOpen) {
      document.body.classList.add('sidebar-open-desktop');
    } else if (typeof document !== 'undefined') {
      document.body.classList.remove('sidebar-open-desktop');
    }

    window.addEventListener('resize', handleResize);
    return () => {
      if (typeof document !== 'undefined') {
        document.body.classList.remove('sidebar-open-desktop');
      }
      window.removeEventListener('resize', handleResize);
    };
  }, [isSidebarOpen, isAuthenticated]);

  const setIsSidebarOpen = (valOrFn) => {
    setIsSidebarOpenState(prev => {
      const next = typeof valOrFn === 'function' ? valOrFn(prev) : valOrFn;
      try {
        localStorage.setItem(STORAGE_KEY, String(next));
      } catch (e) {
        console.warn('Error saving sidebar preference:', e);
      }
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('fc_sidebar_sync', { detail: next }));
      }, 0);
      return next;
    });
  };

  const toggleSidebar = () => setIsSidebarOpen(prev => !prev);
  const closeSidebar = () => setIsSidebarOpen(false);
  const openSidebar = () => setIsSidebarOpen(true);

  return {
    isSidebarOpen: isAuthenticated ? isSidebarOpen : false,
    setIsSidebarOpen,
    toggleSidebar,
    closeSidebar,
    openSidebar
  };
}

export default useSidebar;
