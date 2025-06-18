import React, { useEffect, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import { executeTrade, stopTrade } from '../../services/api';

const LiveTradeResults = ({ onStop, strategy }) => {
  const [tradingStats, setTradingStats] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [currentPosition, setCurrentPosition] = useState(0);
  const [totalPnl, setTotalPnl] = useState(0);
  const [plotData, setPlotData] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const [initializationStatus, setInitializationStatus] = useState({ message: 'Connecting...', progress: 0 });
  const [isInitialized, setIsInitialized] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isStopped, setIsStopped] = useState(false);
  const isStoppingManuallyRef = useRef(false);
  const eventSourceRef = useRef(null);
  const isConnectingRef = useRef(false); // Prevent multiple connection attempts
  const currentStrategyIdRef = useRef(null); // Track current strategy ID

  useEffect(() => {
    // Clean up function declaration
    const cleanup = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      isConnectingRef.current = false;
    };

    // Validate strategy
    if (!strategy || !strategy.strategy_id) {
      setError('No strategy ID provided to LiveTradeResults');
      return cleanup;
    }

    // Check if strategy ID has actually changed
    if (currentStrategyIdRef.current === strategy.strategy_id) {
      console.log('🔍 Strategy ID unchanged, skipping connection setup');
      return cleanup;
    }

    // Prevent multiple connection attempts
    if (isConnectingRef.current || eventSourceRef.current) {
      console.log('🚫 Connection already in progress or exists, skipping...');
      return cleanup;
    }

    console.log('Starting trade execution with strategy ID:', strategy.strategy_id);
    
    // Update current strategy ID reference
    currentStrategyIdRef.current = strategy.strategy_id;
    
    // Execute trade and get EventSource
    const setupTrading = async () => {
      try {
        isConnectingRef.current = true;
        console.log('Setting up trade execution for strategy:', strategy.strategy_id);
        
        // Double-check no existing connection
        if (eventSourceRef.current) {
          console.log('🚫 EventSource already exists, closing old one first');
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        
        const eventSource = await executeTrade(strategy.strategy_id);
        eventSourceRef.current = eventSource;
        isConnectingRef.current = false;
        
        eventSource.onopen = () => {
          console.log('SSE connection opened');
        };
        
        eventSource.onerror = (error) => {
          console.error('SSE Error:', error);
          console.error('ReadyState:', eventSource.readyState);
          
          // Check if this is a manual stop or an actual error
          if (isStoppingManuallyRef.current) {
            console.log('SSE closed due to manual stop - this is expected');
            setIsStopped(true);
            isStoppingManuallyRef.current = false;
            // Don't set error for manual stops
          } else {
            // This is an unexpected error
            setError('Connection error occurred. Please check the console for details.');
          }
          eventSource.close();
          eventSourceRef.current = null;
          isConnectingRef.current = false;
        };
        
        // Listen for specific event types
        eventSource.onmessage = (event) => {
          console.log('Raw event.data received:', event.data);
          console.log('Type of event.data:', typeof event.data);
                      try {
              const update = JSON.parse(event.data);
              console.log('Parsed update:', update);
            
              if (update.status === 'initializing') {
                // Handle initialization progress
                setInitializationStatus({
                  message: update.message,
                  progress: update.progress
                });
                setIsInitialized(false);
              } else if (update.status === 'ready') {
                // Initialization complete
                setInitializationStatus({
                  message: update.message,
                  progress: update.progress
                });
                setIsInitialized(true);
              } else if (update.status === 'processing') {
                // Handle processing updates (show current price but indicate processing)
                setIsInitialized(true);
                setIsProcessing(true);
                if (update.message) {
                  setInitializationStatus({
                    message: update.message,
                    progress: 50 // Show partial progress during processing
                  });
                }
                if (update.price) {
                  setCurrentPrice(update.price);
                }
                if (update.timestamp) {
                  setLastUpdate(update.timestamp);
                }
              } else if (update.status === 'update') {
                // Handle live trading updates
                setIsInitialized(true);
                setIsProcessing(false);
                
                // Update price chart
                if (update.fig) {
                  const figure = JSON.parse(update.fig);
                  setPlotData(figure);
                }
                
                // Update trading stats
                if (update.trading_stats) {
                  setTradingStats(update.trading_stats);
                }
                
                // Update current state
                setCurrentPrice(update.price);
                setCurrentPosition(update.current_position);
                setTotalPnl(update.total_pnl);
                setLastUpdate(update.timestamp);
                
                // Handle trade notifications
                if (update.trade_executed) {
                  const trade = update.trade_executed;
                  console.log(`${trade.type.toUpperCase()} executed at ${trade.price}`);
                }
              } else if (update.status === 'stopped') {
                // Handle trading stopped by backend
                console.log('Trading stopped by backend');
                setIsInitialized(true);
                setIsProcessing(false);
                setIsStopped(true);
                
                // Update final state if provided
                if (update.price) setCurrentPrice(update.price);
                if (update.current_position !== undefined) setCurrentPosition(update.current_position);
                if (update.total_pnl !== undefined) setTotalPnl(update.total_pnl);
                if (update.timestamp) setLastUpdate(update.timestamp);
                
                // Update final data
                if (update.fig) {
                  const figure = JSON.parse(update.fig);
                  setPlotData(figure);
                }
                if (update.trading_stats) {
                  setTradingStats(update.trading_stats);
                }
              }
          } catch (error) {
            console.error('Error parsing SSE data:', error);
            console.error('Raw data that failed to parse:', event.data);
          }
        };
      } catch (error) {
        console.error('Error setting up trade execution:', error);
        setError(`Failed to start trading: ${error.message}`);
        isConnectingRef.current = false;
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      }
    };

    setupTrading();
    return cleanup;
  }, [strategy?.strategy_id]); // Keep the same dependency but add ID tracking

  const handleStop = async () => {
    console.log('Stop button clicked');
    console.log('EventSource exists:', !!eventSourceRef.current);
    console.log('onStop callback exists:', !!onStop);
    console.log('Strategy ID:', strategy?.strategy_id);
    
    // Set flag to indicate manual stop before closing connection
    isStoppingManuallyRef.current = true;
    
    // Close EventSource connection first
    if (eventSourceRef.current) {
      console.log('Closing EventSource connection...');
      eventSourceRef.current.close();
      console.log('EventSource readyState after close:', eventSourceRef.current.readyState);
    }
    
    // Call backend stop endpoint
    if (strategy?.strategy_id) {
      try {
        console.log('Calling backend stop endpoint...');
        const response = await stopTrade(strategy.strategy_id);
        console.log('Backend stop response:', response);
        
        if (response.success) {
          console.log('✅ Trading stopped successfully on backend');
        } else {
          console.warn('⚠️ Backend reported unsuccessful stop:', response.message);
        }
      } catch (error) {
        console.error('❌ Error calling backend stop endpoint:', error);
        // Continue with frontend cleanup even if backend call fails
      }
    } else {
      console.warn('No strategy ID available for backend stop call');
    }
    
    // Call frontend callback to update UI
    if (onStop) {
      console.log('Calling onStop callback...');
      onStop();
    } else {
      console.error('No onStop callback provided!');
    }
  };

  // Show error state if there's an error (but not if stopped)
  if (error && !isStopped) {
    return (
      <div className="w-full">
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-md p-4">
          <p className="font-medium">Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Header with current status */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Live Trading Status</h3>
          <p className="text-sm text-gray-500">
            {isStopped
              ? `🛑 Trading stopped at: ${lastUpdate ? new Date(lastUpdate).toLocaleString() : 'N/A'}`
              : !isInitialized 
                ? initializationStatus.message
                : isProcessing
                  ? `🔄 ${initializationStatus.message || "Processing new data..."}`
                  : `Last update: ${lastUpdate ? new Date(lastUpdate).toLocaleString() : 'N/A'}`
            }
          </p>
        </div>
        {!isStopped && (
          <button
            onClick={handleStop}
            className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Stop Trading
          </button>
        )}
        {isStopped && (
          <div className="px-4 py-2 bg-gray-500 text-white rounded-md">
            Trading Stopped
          </div>
        )}
      </div>

      {/* Initialization Progress Bar */}
      {!isInitialized && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-blue-700">Initializing Trade Monitor</span>
            <span className="text-sm text-blue-600">{initializationStatus.progress}%</span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${initializationStatus.progress}%` }}
            />
          </div>
          <p className="text-sm text-blue-600 mt-2">{initializationStatus.message}</p>
        </div>
      )}

      {/* Current position and PnL */}
      {isInitialized && (
        <>
          <div className="grid grid-cols-3 gap-6 mb-6">
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="text-sm font-medium text-gray-500">Current Price</h3>
              <p className="text-2xl font-semibold text-gray-900">
                ${currentPrice ? currentPrice.toFixed(4) : 'N/A'}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="text-sm font-medium text-gray-500">Position</h3>
              <p className="text-2xl font-semibold text-gray-900">
                {currentPosition ? 'LONG' : 'FLAT'}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="text-sm font-medium text-gray-500">Total PnL</h3>
              <p className={`text-2xl font-semibold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalPnl ? `${totalPnl.toFixed(2)}%` : '0.00%'}
              </p>
            </div>
          </div>

          {/* Trading Stats */}
          {tradingStats && (
            <div className="bg-white p-6 rounded-lg shadow mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Trading Statistics</h3>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Total Trades</p>
                  <p className="text-xl font-semibold">{tradingStats.total_trades}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Win Rate</p>
                  <p className="text-xl font-semibold">{tradingStats.win_rate?.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total Return</p>
                  <p className={`text-xl font-semibold ${tradingStats.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {tradingStats.total_return?.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Avg Return per Trade</p>
                  <p className={`text-xl font-semibold ${tradingStats.avg_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {tradingStats.avg_return?.toFixed(2)}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Price Chart */}
          {plotData && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <Plot
                data={plotData.data}
                layout={{
                  ...plotData.layout,
                  autosize: true,
                  height: 500,
                  margin: { l: 50, r: 50, t: 30, b: 30 }
                }}
                useResizeHandler={true}
                className="w-full"
              />
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default LiveTradeResults; 