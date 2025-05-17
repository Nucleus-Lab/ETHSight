import React, { useEffect, useState } from 'react';
import { getCanvasFirstMessage, getCanvasFirstVisualization } from '../../services/api';
import Plot from 'react-plotly.js';

const CanvasCard = ({ canvasId, onClick }) => {
  const [preview, setPreview] = useState({
    message: null,
    visualization: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    const loadPreviews = async () => {
      try {
        const [messageRes, visualizationRes] = await Promise.all([
          getCanvasFirstMessage(canvasId),
          getCanvasFirstVisualization(canvasId)
        ]);

        setPreview({
          message: messageRes,
          visualization: visualizationRes,
          loading: false,
          error: null
        });
      } catch (error) {
        console.error('Error loading canvas previews:', error);
        setPreview(prev => ({
          ...prev,
          loading: false,
          error: 'Failed to load preview'
        }));
      }
    };

    loadPreviews();
  }, [canvasId]);

  // Parse and validate Plotly data
  const plotlyData = React.useMemo(() => {
    if (!preview.visualization?.json_data) return null;

    try {
      const parsedData = typeof preview.visualization.json_data === 'string' 
        ? JSON.parse(preview.visualization.json_data) 
        : preview.visualization.json_data;

      if (!parsedData?.data || !Array.isArray(parsedData.data)) {
        console.error('CanvasCard - Invalid plot data structure:', parsedData);
        return null;
      }

      return parsedData;
    } catch (error) {
      console.error('CanvasCard - Error parsing plot data:', error);
      return null;
    }
  }, [preview.visualization?.json_data]);

  if (preview.loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-4 w-full max-w-sm h-48 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="h-32 bg-gray-200 rounded"></div>
      </div>
    );
  }

  return (
    <div 
      onClick={onClick}
      className="bg-white rounded-lg shadow-md p-4 w-full max-w-sm hover:shadow-lg transition-shadow duration-200 cursor-pointer"
    >
      {/* Message Preview */}
      <div className="mb-4">
        <p className="text-sm text-gray-600 line-clamp-2">
          {preview.message?.text || 'No message preview available'}
        </p>
        <span className="text-xs text-gray-400">
          {preview.message?.created_at && new Date(preview.message.created_at).toLocaleDateString()}
        </span>
      </div>

      {/* Visualization Preview */}
      <div className="h-32 bg-gray-50 rounded-md overflow-hidden">
        {plotlyData ? (
          <Plot
            data={plotlyData.data}
            layout={{
              ...plotlyData.layout,
              autosize: true,
              margin: { l: 25, r: 25, t: 25, b: 25 }, // Smaller margins for preview
              showlegend: false, // Hide legend in preview
              height: 128, // Match container height
              width: null, // Let it be responsive
              title: null, // Remove title in preview
              font: { size: 8 }, // Smaller font for preview
            }}
            config={{
              displayModeBar: false, // Hide the mode bar in preview
              responsive: true,
              staticPlot: true, // Make it non-interactive for preview
            }}
            className="w-full h-full"
            style={{ height: '128px' }} // Fixed height for preview
            onError={(err) => {
              console.error('CanvasCard - Plot error:', err);
            }}
          />
        ) : (
          <div className="h-full flex items-center justify-center">
            <span className="text-sm text-gray-400">No visualization available</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CanvasCard; 