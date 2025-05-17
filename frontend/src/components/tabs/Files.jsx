import React, { useEffect, useState } from 'react';
import { usePrivy } from '@privy-io/react-auth';
import { getUserCanvases } from '../../services/api';
import { useCanvas } from '../../contexts/CanvasContext';
import { useChatContext } from '../../contexts/ChatContext';
import CanvasCard from '../canvas/CanvasCard';

const Files = () => {
  const { user, authenticated } = usePrivy();
  const { setCurrentCanvasId } = useCanvas();
  const { setIsChatOpen } = useChatContext();
  const [canvases, setCanvases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadCanvases = async () => {
      if (!authenticated || !user?.wallet?.address) {
        setLoading(false);
        return;
      }

      try {
        const userCanvases = await getUserCanvases(user.wallet.address);
        setCanvases(userCanvases);
        setError(null);
      } catch (error) {
        console.error('Error loading canvases:', error);
        setError('Failed to load canvases');
      } finally {
        setLoading(false);
      }
    };

    loadCanvases();
  }, [authenticated, user?.wallet?.address]);

  if (!authenticated) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-gray-500">Please connect your wallet to view your files</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-100 h-48 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  if (canvases.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-gray-500">No files yet. Start a conversation to create one!</p>
      </div>
    );
  }

  const handleCanvasClick = (canvasId) => {
    setCurrentCanvasId(canvasId);
    setIsChatOpen(true); // Open the chat interface
  };

  return (
    <div className="p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {canvases.map((canvas) => (
          <CanvasCard
            key={canvas.canvas_id}
            canvasId={canvas.canvas_id}
            onClick={() => handleCanvasClick(canvas.canvas_id)}
          />
        ))}
      </div>
    </div>
  );
};

export default Files; 