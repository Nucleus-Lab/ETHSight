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

  return (
    <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-gray-800">{result.name}</h2>
        <p className="text-gray-600">{result.description}</p>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 p-3 rounded-md">
          <p className="text-sm text-gray-500">Total Return</p>
          <p className="text-2xl font-semibold text-gray-800">
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
          <p className="text-2xl font-semibold text-gray-800">
            {formatPercentage(result.performance.drawdown)}
          </p>
        </div>
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
              showlegend: false,
            }}
            config={{
              displayModeBar: false,
              responsive: true,
            }}
            style={{ width: '100%', height: '100%' }}
          />
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
        <button className="px-4 py-2 bg-primary-main text-black rounded hover:bg-primary-hover transition-colors">
          Deploy Strategy
        </button>
      </div>
    </div>
  );
};

export default BacktestResultCard; 