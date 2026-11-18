import React, { useState, useEffect } from 'react';
import announcementService from '../../services/announcementService';
import { usePermissions } from '../../hooks/usePermissions';

const PopupBanner = () => {
  const { isAuthenticated, isStaff, loading } = usePermissions();
  const [announcement, setAnnouncement] = useState(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Esperar resolución de autenticación
    if (loading) return;

    // Si es personal interno del sistema (staff), no mostrar popups promocionales
    if (isAuthenticated && isStaff) {
      return;
    }

    // Comprobar si ya se mostró en esta sesión
    const hasSeenPopup = sessionStorage.getItem('hasSeenPopup');
    if (hasSeenPopup) return;

    const fetchPopup = async () => {
      try {
        const data = await announcementService.getPopup();
        if (data && data.id) {
          setAnnouncement(data);
          setIsVisible(true);
        }
      } catch (error) {
        console.error("No popup available or error fetching popup:", error);
      }
    };

    fetchPopup();
  }, [loading, isAuthenticated, isStaff]);

  const handleClose = () => {
    setIsVisible(false);
    sessionStorage.setItem('hasSeenPopup', 'true');
  };

  if (loading || (isAuthenticated && isStaff)) return null;
  if (!isVisible || !announcement) return null;

  return (
    <div className="popup-overlay" onClick={handleClose}>
      <div className="popup-content" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={handleClose}>&times;</button>
        <h2>{announcement.title}</h2>
        {announcement.content && <p>{announcement.content}</p>}
        {announcement.img_url && <img src={announcement.img_url} alt={announcement.title} />}
      </div>
    </div>
  );
};

export default PopupBanner;
