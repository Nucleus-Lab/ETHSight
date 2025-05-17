import React, { useState, useEffect, useRef } from 'react';
import VisualizationCard from '../visualization/VisualizationCard';
import { getVisualization, getCanvasVisualizations, getSignalsForCanvas } from '../../services/api';
import { useCanvas } from '../../contexts/CanvasContext';
import { usePrivy } from '@privy-io/react-auth';
import WelcomeAnimation from '../common/WelcomeAnimation';
import { useChatContext } from '../../contexts/ChatContext';

const Canvas = ({ visualizationIds = [], setActiveVisualizations }) => {
  const { currentCanvasId } = useCanvas();
  const { authenticated, user } = usePrivy();
  const { setChatInputText } = useChatContext();
  const [visualizations, setVisualizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showSignals, setShowSignals] = useState(false);
  const [canvasSignals, setCanvasSignals] = useState([]);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const bottomRef = useRef(null);
  const visualizationRefs = useRef({});

  // Rest of your existing useEffect blocks...

  // Fetch signals when the button is clicked
  const fetchCanvasSignals = async () => {
    if (!currentCanvasId) return;
    
    setLoadingSignals(true);
    try {
      const signals = await getSignalsForCanvas(currentCanvasId);
      setCanvasSignals(signals);
      setShowSignals(true);
    } catch (error) {
      console.error('Error fetching canvas signals:', error);
    } finally {
      setLoadingSignals(false);
    }
  };

  // Add signal to chat
  const addSignalToChat = (signalId) => {
    setChatInputText((currentText) => {
      const prefix = currentText && !currentText.endsWith(' ') ? ' ' : '';
      return `${currentText}${prefix}@signal:${signalId}`;
    });
    setShowSignals(false);
  };

  // Your existing code...

  return (
    <div className="flex flex-col w-full space-y-6 p-4 overflow-y-auto relative">
      {visualizations.map((visualization, index) => (
        <div 
          key={`viz-${visualization.id || index}`}
          ref={visualizationRefs.current[visualization.id] || null}
        >
          <VisualizationCard
            plotData={visualization.data}
            visualizationId={visualization.id}
          />
        </div>
      ))}
      <div ref={bottomRef} /> {/* Add ref for auto-scrolling */}
      
      {/* Signals Button */}
      {currentCanvasId && (
        <button
          onClick={fetchCanvasSignals}
          className="fixed right-6 bottom-6 p-3 bg-primary-main text-black rounded-full shadow-lg hover:bg-primary-hover focus:outline-none"
          title="View Canvas Signals"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </button>
      )}
      
      {/* Signals Modal */}
      {showSignals && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="flex justify-between items-center border-b p-4">
              <h3 className="text-lg font-semibold">Canvas Signals</h3>
              <button onClick={() => setShowSignals(false)} className="text-gray-500 hover:text-gray-700">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-4 overflow-auto max-h-[calc(80vh-8rem)]">
              {loadingSignals ? (
                <div className="flex justify-center p-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-main"></div>
                </div>
              ) : canvasSignals.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No signals found for this canvas</p>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Definition</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {canvasSignals.map((signal) => (
                      <tr key={signal.signal_id} className="hover:bg-gray-50">
                        <td className="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                          {signal.signal_id}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-500 max-w-xs truncate">
                          {signal.signal_definition}
                        </td>
                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                          {new Date(signal.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 whitespace-nowrap text-right text-sm font-medium">
                          <button
                            onClick={() => addSignalToChat(signal.signal_id)}
                            className="px-3 py-1 bg-primary-main text-black rounded hover:bg-primary-hover transition-colors duration-200"
                          >
                            Use for backtest
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            
            <div className="border-t p-4 flex justify-end">
              <button
                onClick={() => setShowSignals(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Canvas; 