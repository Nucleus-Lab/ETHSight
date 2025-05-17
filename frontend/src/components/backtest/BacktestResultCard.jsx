import React from 'react';
import Plot from 'react-plotly.js';

const BacktestResultCard = ({ result, resultId }) => {
  console.log('Rendering BacktestResultCard for result:', resultId);

  if (!result) {
    return (
      <div className="bg-white p-4 rounded-lg shadow-md border border-gray-200">
        <p className="text-gray-500">Result data not available</p>
      </div>
    );
  }

  // Format performance metrics
  const formatPercentage = (value) => `${parseFloat(value).toFixed(2)}%`;
  const formatNumber = (value) => parseFloat(value).toFixed(2);
  
  // Determine card styling based on whether this is a live trade or backtest
  const cardBorderClass = result.isLiveTrade
    ? "border-red-300"
    : "border-gray-200";
  
  // Determine badge text and style
  const badgeText = result.isLiveTrade ? "LIVE TRADE" : "BACKTEST";
  const badgeClass = result.isLiveTrade
    ? "bg-red-100 text-red-800"
    : "bg-blue-100 text-blue-800";

  return (
    <div className={`bg-white p-6 rounded-lg shadow-md border ${cardBorderClass}`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">{result.name}</h2>
          <p className="text-gray-600">{result.description}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${badgeClass}`}>
          {badgeText}
        </span>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-gray-50 p-3 rounded-md">
          <p className="text-sm text-gray-500">Total Return</p>
          <p className={`text-2xl font-semibold ${
            result.performance.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {formatPercentage(result.performance.totalReturn)}
          </p>
        </div>
        
        <div className="bg-gray-50 p-3 rounded-md">
          <p className="text-sm text-gray-500">Sharpe Ratio</p>
          <p className="text-2xl font-semibold text-gray-800">
            {formatNumber(result.performance.sharpeRatio)}
          </p>
        </div>
        
        <div className="bg-gray-50 p-3 rounded-md">
          <p className="text-sm text-gray-500">Max Drawdown</p>
          <p className="text-2xl font-semibold text-red-600">
            {formatPercentage(result.performance.maxDrawdown)}
          </p>
        </div>
        
        {result.performance.winRate && (
          <div className="bg-gray-50 p-3 rounded-md">
            <p className="text-sm text-gray-500">Win Rate</p>
            <p className="text-2xl font-semibold text-gray-800">
              {formatPercentage(result.performance.winRate)}
            </p>
          </div>
        )}
        
        {result.performance.trades && (
          <div className="bg-gray-50 p-3 rounded-md">
            <p className="text-sm text-gray-500">Trades</p>
            <p className="text-2xl font-semibold text-gray-800">
              {result.performance.trades}
            </p>
          </div>
        )}
      </div>

      {/* Chart */}
      <div className="h-64 w-full">
        {result.data ? (
          <Plot
            data={[
              {
                x: result.data.x,
                y: result.data.y,
                type: result.data.type || 'scatter',
                mode: result.data.mode || 'lines',
                name: result.data.name || 'Performance',
                line: { color: '#ffde0f' },
              },
              // Add buy points if present
              ...(result.data.tradePoints ? [{
                x: result.data.tradePoints.filter(point => point.type === 'buy').map(point => point.date),
                y: result.data.tradePoints.filter(point => point.type === 'buy').map(point => point.value),
                type: 'scatter',
                mode: 'markers',
                marker: { color: 'green', symbol: 'triangle-up', size: 12 },
                name: 'Buy'
              }] : []),
              // Add sell points if present
              ...(result.data.tradePoints ? [{
                x: result.data.tradePoints.filter(point => point.type === 'sell').map(point => point.date),
                y: result.data.tradePoints.filter(point => point.type === 'sell').map(point => point.value),
                type: 'scatter',
                mode: 'markers',
                marker: { color: 'red', symbol: 'triangle-down', size: 12 },
                name: 'Sell'
              }] : []),
            ]}
            layout={{
              autosize: true,
              margin: { l: 40, r: 20, t: 20, b: 40 },
              xaxis: {
                title: 'Date',
                showgrid: false,
              },
              yaxis: {
                title: 'Value ($)',
                showgrid: true,
                gridcolor: '#f0f0f0',
              },
              paper_bgcolor: 'white',
              plot_bgcolor: 'white',
              showlegend: true,
              legend: {
                orientation: 'h', 
                x: 0, 
                y: -0.2
              }
            }}
            config={{
              displayModeBar: false,
              responsive: true,
            }}
            style={{ width: '100%', height: '100%' }}
          />
        ) : result.isLiveTrade ? (
          <div className="h-full w-full flex items-center justify-center bg-gray-50 p-6 rounded border border-gray-200">
            <div className="text-center">
              <p className="text-gray-500 mb-2">Live trade in progress</p>
              <p className="text-sm text-gray-400">Chart data will be updated as trades are executed</p>
            </div>
          </div>
        ) : (
          <div className="h-full w-full flex items-center justify-center">
            <p className="text-gray-500">No chart data available</p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mt-6 flex justify-end space-x-4">
        <button className="px-4 py-2 bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition-colors">
          View Details
        </button>
        {!result.isLiveTrade && (
          <button className="px-4 py-2 bg-primary-main text-black rounded hover:bg-primary-hover transition-colors">
            Deploy Strategy
          </button>
        )}
        {result.isLiveTrade && (
          <button className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
            Stop Trading
          </button>
        )}
      </div>
    </div>
  );
};

export default BacktestResultCard; 