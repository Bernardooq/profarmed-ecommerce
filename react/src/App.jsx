import { useEffect } from 'react';
import { HelmetProvider } from 'react-helmet-async';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './routes/ProtectedRoute';
import ScrollToTop from './components/common/ScrollToTop';
import IOSInstallPrompt from './components/common/IOSInstallPrompt';
import Login from './pages/Login';
import Home from './pages/Home';
import PopupBanner from './components/announcements/PopupBanner';
import FooterBanner from './components/announcements/FooterBanner';
import Products from './pages/Products';
import PromoAdsHome from './pages/PromoAdsHome';
import Promos from './pages/Promos';
import Cart from './pages/Cart';
import FavoriteLists from './pages/FavoriteLists';
import FavoriteListDetails from './pages/FavoriteListDetails';
import Profile from './pages/Profile';
import Orders from './pages/Orders';
import Support from './pages/Support';

import UnifiedDashboard from './pages/UnifiedDashboard';
import Contact from './pages/Contact';
import AboutUs from './pages/AboutUs';
import TermsAndConditions from './pages/TermsAndConditions';
import PrivacyPolicy from './pages/PrivacyPolicy';

import BeClient from './pages/BeClient';
import PublicCatalog from './pages/PublicCatalog';
import PublicProductDetail from './pages/PublicProductDetail';
import { PERMISSIONS } from './config/permissions';
import BRAND from './config/brand';
import { syncThemeMeta } from './hooks/useTheme';

function App() {
  useEffect(() => {
    document.title = BRAND.getTitle();
    syncThemeMeta();
  }, []);

  return (
    <HelmetProvider>
      <ScrollToTop />
      <IOSInstallPrompt />
      <PopupBanner />
      <FooterBanner />
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Home />} />
        <Route path="/catalogo" element={<PublicCatalog />} />
        <Route path="/catalogo-publico" element={<PublicCatalog />} />
        <Route path="/catalogo/producto/:productId" element={<PublicProductDetail />} />
        <Route path="/producto/:productId" element={<PublicProductDetail />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/about" element={<AboutUs />} />
        <Route path="/terms" element={<TermsAndConditions />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/quiero-ser-cliente" element={<BeClient />} />

        {/* Protected routes - require authentication */}
        <Route
          path="/novedades"
          element={
            <ProtectedRoute permission={PERMISSIONS.CATALOG_VIEW}>
              <PromoAdsHome />
            </ProtectedRoute>
          }
        />

        <Route
          path="/products"
          element={
            <ProtectedRoute permission={PERMISSIONS.CATALOG_VIEW}>
              <Products />
            </ProtectedRoute>
          }
        />

        {/* Protected routes - require authentication */}
        <Route
          path="/promos"
          element={
            <ProtectedRoute permission={PERMISSIONS.ANNOUNCEMENTS_VIEW}>
              <Promos />
            </ProtectedRoute>
          }
        />

        <Route
          path="/cart"
          element={
            <ProtectedRoute>
              <Cart />
            </ProtectedRoute>
          }
        />
        <Route
          path="/favorites"
          element={
            <ProtectedRoute>
              <FavoriteLists />
            </ProtectedRoute>
          }
        />
        <Route
          path="/favorites/:id"
          element={
            <ProtectedRoute>
              <FavoriteListDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/orders"
          element={
            <ProtectedRoute permission={PERMISSIONS.ORDERS_VIEW}>
              <Orders />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/support"
          element={
            <ProtectedRoute permission={PERMISSIONS.SUPPORT_VIEW}>
              <Support />
            </ProtectedRoute>
          }
        />

        {/* Dashboard Universal Dinámico (PBAC / RBAC) */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <UnifiedDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/userdashboard"
          element={
            <ProtectedRoute>
              <UnifiedDashboard />
            </ProtectedRoute>
          }
        />

      </Routes>
    </HelmetProvider>
  );
}

export default App;