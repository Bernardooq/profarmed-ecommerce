import React, { useState, useEffect } from 'react';
import announcementService from '../../services/announcementService';
import { usePermissions } from '../../hooks/usePermissions';

const FooterBanner = () => {
  const { isAuthenticated, isStaff, loading } = usePermissions();
  const [announcement, setAnnouncement] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    // Wait until auth state is resolved
    if (loading) return;

    // Si es personal interno del sistema (staff), no consultar ni desplegar banner inferior
    if (isAuthenticated && isStaff) {
      return;
    }

    const fetchFooter = async () => {
      try {
        const data = await announcementService.getFooter();
        if (data && data.id) {
          setAnnouncement(data);
        }
      } catch (error) {
        console.error("No footer available or error fetching footer:", error);
      }
    };

    fetchFooter();
  }, [loading, isAuthenticated, isStaff]);

  if (loading || (isAuthenticated && isStaff)) return null;
  if (!announcement) return null;

  return (
    <div className={`footer-banner ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="banner-content">
        {announcement.img_url && <img src={announcement.img_url} alt={announcement.title} />}
        <div>
          <h4>{announcement.title}</h4>
          {announcement.content && <p>{announcement.content}</p>}
        </div>
      </div>
      <button className="close-btn" onClick={() => setIsCollapsed(true)} title="Cerrar banner">
        &times;
      </button>
    </div>
  );
};

export default FooterBanner;
