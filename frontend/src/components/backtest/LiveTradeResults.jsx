import React, { useEffect, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import { stopTrade } from '../../services/api';

const LiveTradeResults = ({ onStop, strategy }) => {
  console.log('🔄 LiveTradeResults RENDER - strategy:', strategy);
  console.log('🔄 LiveTradeResults RENDER - strategy keys:', strategy ? Object.keys(strategy) : 'null');
  console.log('🔄 LiveTradeResults RENDER - strategy object reference:', strategy);
  
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
  const lastStrategyIdRef = useRef(null);
  const lastStrategyRef = useRef(null);
  const hasRunOnce = useRef(false);


  console.log('🔄 LiveTradeResults RENDER - current tradingStats:', tradingStats);
  console.log('🔄 LiveTradeResults RENDER - current currentPrice:', currentPrice);
  console.log('🔄 LiveTradeResults RENDER - current currentPosition:', currentPosition);
  console.log('🔄 LiveTradeResults RENDER - current totalPnl:', totalPnl);
  console.log('🔄 LiveTradeResults RENDER - current plotData:', plotData);
  console.log('🔄 LiveTradeResults RENDER - current lastUpdate:', lastUpdate);
  console.log('🔄 LiveTradeResults RENDER - current error:', error);
  console.log('🔄 LiveTradeResults RENDER - current initializationStatus:', initializationStatus);
  console.log('🔄 LiveTradeResults RENDER - current isInitialized:', isInitialized);
  console.log('🔄 LiveTradeResults RENDER - current isProcessing:', isProcessing);
  console.log('🔄 LiveTradeResults RENDER - current isStopped:', isStopped);
  

  useEffect(() => {
    console.log('🔄 LiveTradeResults useEffect TRIGGERED');
    console.log('🔄 LiveTradeResults dependencies - strategy.strategy_id:', strategy?.strategy_id);
    let didCancel = false;

    const cleanup = () => {
      console.log('🧼 Attempting cleanup. eventSourceRef.current:', eventSourceRef.current, hasRunOnce.current);
      hasRunOnce.current = false;
      if (eventSourceRef.current) {
        console.log('✅ Closing EventSource');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };

    if (!strategy || !strategy.strategy_id || !strategy.createEventSource) {
      console.warn('❌ Missing strategy or SSE factory');
      return cleanup;
    }

    if (hasRunOnce.current) {
      console.log('🛑 Already connected once — skipping duplicate');
      return cleanup;
    }

    hasRunOnce.current = true;

    const setup = async () => {
      try {
        const eventSource = await strategy.createEventSource();
        // to avoid re-creating the event source if the component is unmounted, especially in Strict Mode
        if (didCancel) {
          console.warn('🛑 Setup aborted: component unmounted or effect re-ran');
          eventSource?.close();
          return;
        }

        eventSourceRef.current = eventSource;
        
        eventSource.onopen = () => {
          console.log('SSE connection opened');
        };
        
        eventSource.onerror = (error) => {
          console.error('SSE Error:', error);
          console.error('ReadyState:', eventSource.readyState);
          
          if (isStoppingManuallyRef.current) {
            console.log('SSE closed due to manual stop - this is expected');
            setIsStopped(true);
            isStoppingManuallyRef.current = false;
          } else {
            setError('Connection error occurred. Please check the console for details.');
          }
          eventSource.close();
          eventSourceRef.current = null;
        };
        
        eventSource.onmessage = (event) => {
          console.log('Raw event.data received:', event.data);
          console.log('Type of event.data:', typeof event.data);
          try {
            const update = JSON.parse(event.data);
            console.log('Parsed update:', update);
          
            if (update.status === 'initializing') {
              setInitializationStatus({
                message: update.message,
                progress: update.progress
              });
              setIsInitialized(false);
            } else if (update.status === 'ready') {
              setInitializationStatus({
                message: update.message,
                progress: update.progress
              });
              setIsInitialized(true);
            } else if (update.status === 'processing') {
              setIsInitialized(true);
              setIsProcessing(true);
              if (update.message) {
                setInitializationStatus({
                  message: update.message,
                  progress: 50
                });
              }
              if (update.price) {
                setCurrentPrice(update.price);
              }
              if (update.timestamp) {
                setLastUpdate(update.timestamp);
              }
            } else if (update.status === 'update') {
              setIsInitialized(true);
              setIsProcessing(false);
              
              if (update.fig) {
                const figure = JSON.parse(update.fig);
                setPlotData(figure);
              }
              
              if (update.trading_stats) {
                setTradingStats(update.trading_stats);
              }
              
              setCurrentPrice(update.price);
              setCurrentPosition(update.current_position);
              setTotalPnl(update.total_pnl);
              setLastUpdate(update.timestamp);
              
              if (update.trade_executed) {
                const trade = update.trade_executed;
                console.log(`${trade.type.toUpperCase()} executed at ${trade.price}`);
              }
            } else if (update.status === 'stopped') {
              console.log('Trading stopped by backend');
              setIsInitialized(true);
              setIsProcessing(false);
              setIsStopped(true);
              
              if (update.price) setCurrentPrice(update.price);
              if (update.current_position !== undefined) setCurrentPosition(update.current_position);
              if (update.total_pnl !== undefined) setTotalPnl(update.total_pnl);
              if (update.timestamp) setLastUpdate(update.timestamp);
              
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
        if (!didCancel) {
          setError(`Failed to start trading: ${error.message}`);
        }
      }
    };

    setup();

    return () => {
      didCancel = true;
      cleanup();
    };
  }, [strategy?.strategy_id]);

  const handleStop = async () => {
    console.log('Stop button clicked');
    console.log('EventSource exists:', !!eventSourceRef.current);
    console.log('onStop callback exists:', !!onStop);
    console.log('Strategy ID:', strategy?.strategy_id);
    
    isStoppingManuallyRef.current = true;
    setIsStopped(true);
    
    if (eventSourceRef.current) {
      console.log('Closing EventSource connection...');
      eventSourceRef.current.close();
      console.log('EventSource readyState after close:', eventSourceRef.current.readyState);
    }
     
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
      }
    } else {
      console.warn('No strategy ID available for backend stop call');
    }
    
    if (onStop) {
      console.log('Calling onStop callback...');
      onStop();
    } else {
      console.error('No onStop callback provided!');
    }
  };

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