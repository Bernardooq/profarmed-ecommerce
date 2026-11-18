import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import App from './App.jsx';
import './styles/main.scss';

import { PaginationLimitProvider } from './context/PaginationLimitContext';
import { syncThemeMeta } from './hooks/useTheme';

// Apply saved theme before render to prevent flash (defaults to light)
const savedTheme = typeof window !== 'undefined' ? localStorage.getItem('theme') : 'light';
if (savedTheme === 'dark') {
  document.documentElement.setAttribute('data-theme', 'dark');
  document.documentElement.style.colorScheme = 'dark';
} else {
  document.documentElement.removeAttribute('data-theme');
  document.documentElement.style.colorScheme = 'light';
}
syncThemeMeta();

// Clean up any stale/zombie Service Workers or cached shells from legacy PWA versions
if (typeof window !== 'undefined') {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      for (const registration of registrations) {
        registration.unregister();
      }
    }).catch(() => {});
  }
  if ('caches' in window) {
    caches.keys().then((keys) => {
      for (const key of keys) {
        caches.delete(key);
      }
    }).catch(() => {});
  }
}


ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <AuthProvider>
      <PaginationLimitProvider>
        <CartProvider>
          <App />
        </CartProvider>
      </PaginationLimitProvider>
    </AuthProvider>
  </BrowserRouter>
);