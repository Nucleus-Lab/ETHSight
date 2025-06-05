import React, { useEffect, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import { executeTrade } from '../../services/api';

const LiveTradeResults = ({ onStop, strategy }) => {
  const [tradingStats, setTradingStats] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [currentPosition, setCurrentPosition] = useState(0);
  const [totalPnl, setTotalPnl] = useState(0);
  const [plotData, setPlotData] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    // Clean up function declaration
    const cleanup = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };

    // Validate strategy
    if (!strategy || !strategy.strategy_id) {
      setError('No strategy ID provided to LiveTradeResults');
      return cleanup;
    }

    console.log('Starting trade execution with strategy ID:', strategy.strategy_id);
    
    // Execute trade and get EventSource
    const setupTrading = async () => {
      try {
        const eventSource = await executeTrade(strategy.strategy_id);
        eventSourceRef.current = eventSource;
        
        // Listen for specific event types
        eventSource.onmessage = (event) => {
          const update = JSON.parse(event.data);
          console.log('Received update:', update);
          
          if (update.status === 'update') {
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
          }
        };

        eventSource.onerror = (error) => {
          console.error('SSE Error:', error);
          setError('Connection error occurred');
          eventSource.close();
        };
      } catch (error) {
        console.error('Error setting up trade execution:', error);
        setError('Failed to start trading');
      }
    };

    setupTrading();
    return cleanup;
  }, [strategy]);

  const handleStop = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (onStop) {
      onStop();
    }
  };

  // Show error state if there's an error
  if (error) {
    return (
      <div className="w-full max-w-6xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-md p-4">
          <p className="font-medium">Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      {/* Header with current status */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-gray-800">Live Trading</h2>
          <p className="text-sm text-gray-500">
            Last update: {lastUpdate ? new Date(lastUpdate).toLocaleString() : 'N/A'}
          </p>
        </div>
        <button
          onClick={handleStop}
          className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          Stop Trading
        </button>
      </div>

      {/* Current position and PnL */}
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
        <div className="bg-white p-6 rounded-lg shadow">
          <Plot
            data={plotData.data}
            layout={{
              ...plotData.layout,
              autosize: true,
              height: 600,
              margin: { l: 50, r: 50, t: 30, b: 30 }
            }}
            useResizeHandler={true}
            className="w-full"
          />
        </div>
      )}
    </div>
  );
};

export default LiveTradeResults; 