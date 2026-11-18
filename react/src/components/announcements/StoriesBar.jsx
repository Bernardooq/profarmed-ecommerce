import React, { useState, useEffect } from 'react';
import announcementService from '../../services/announcementService';
import { usePermissions } from '../../hooks/usePermissions';
import StoryViewerModal from './StoryViewerModal';

const StoriesBar = () => {
  const { isAuthenticated, isCustomer } = usePermissions();
  const [stories, setStories] = useState([]);
  const [activeStory, setActiveStory] = useState(null);

  useEffect(() => {
    // Solo consultar historias si está autenticado como cliente
    if (!isAuthenticated || !isCustomer) return;

    const fetchStories = async () => {
      try {
        const data = await announcementService.getStories();
        if (data && data.length > 0) {
          setStories(data);
        }
      } catch (error) {
        console.error("No stories available or error fetching stories:", error);
      }
    };

    fetchStories();
  }, [isAuthenticated, isCustomer]);

  // No renderizar si no es cliente o no hay historias activas
  if (!isAuthenticated || !isCustomer || stories.length === 0) return null;

  return (
    <>
      <div className="stories-container">
        {stories.map(story => (
          <div key={story.id} className="story-item" onClick={() => setActiveStory(story)}>
            <div className="story-ring">
              <img src={story.img_url || 'https://via.placeholder.com/70'} alt={story.title} />
            </div>
            <span>{story.title}</span>
          </div>
        ))}
      </div>

      {activeStory && (
        <StoryViewerModal
          story={activeStory}
          stories={stories}
          onClose={() => setActiveStory(null)}
          duration={6000}
        />
      )}
    </>
  );
};

export default StoriesBar;
