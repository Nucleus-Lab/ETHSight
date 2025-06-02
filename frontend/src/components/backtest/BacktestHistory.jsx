import React, { useState, useEffect } from 'react';
import { usePrivy } from '@privy-io/react-auth';
import { getUserBacktestHistories } from '../../services/api';
import { CalendarIcon, ChartBarIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline';

const BacktestHistory = () => {
  const { user } = usePrivy();
  const [histories, setHistories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user?.wallet?.address) {
      fetchBacktestHistories();
    }
  }, [user?.wallet?.address]);

  const fetchBacktestHistories = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await getUserBacktestHistories(user.wallet.address);
      setHistories(data);
      
      console.log('Fetched backtest histories:', data);
    } catch (err) {
      console.error('Error fetching backtest histories:', err);
      setError('Failed to load backtest histories');
    } finally {
      setLoading(false);
    }
  };

  const formatPercentage = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return `${parseFloat(value).toFixed(2)}%`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getReturnColor = (value) => {
    if (value === null || value === undefined) return 'text-gray-500';
    return value >= 0 ? 'text-green-600' : 'text-red-600';
  };

  const getReturnIcon = (value) => {
    if (value === null || value === undefined) return null;
    return value >= 0 ? (
      <ArrowTrendingUpIcon className="h-4 w-4 text-green-600" />
    ) : (
      <ArrowTrendingDownIcon className="h-4 w-4 text-red-600" />
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-main"></div>
        <span className="ml-2 text-gray-600">Loading backtest histories...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-600 mb-2">{error}</div>
        <button
          onClick={fetchBacktestHistories}
          className="px-4 py-2 bg-primary-main text-black rounded hover:bg-primary-hover transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (histories.length === 0) {
    return (
      <div className="text-center py-12">
        <ChartBarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Backtest History</h3>
        <p className="text-gray-500">
          Run your first backtest to see the results here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-900">Backtest History</h2>
        <span className="text-sm text-gray-500">{histories.length} backtest{histories.length !== 1 ? 's' : ''}</span>
      </div>

      <div className="space-y-4">
        {histories.map((history) => (
          <div key={history.backtest_id} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            {/* Header */}
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  Strategy #{history.strategy_id}
                </h3>
                <div className="flex items-center text-sm text-gray-500 mt-1">
                  <CalendarIcon className="h-4 w-4 mr-1" />
                  <span>Backtested on {formatDateTime(history.created_at)}</span>
                </div>
              </div>
              <div className="flex items-center">
                {getReturnIcon(history.total_return)}
                <span className={`ml-1 text-lg font-semibold ${getReturnColor(history.total_return)}`}>
                  {formatPercentage(history.total_return)}
                </span>
              </div>
            </div>

            {/* Performance Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
              <div className="text-center">
                <p className="text-sm text-gray-500">Total Return</p>
                <p className={`text-lg font-semibold ${getReturnColor(history.total_return)}`}>
                  {formatPercentage(history.total_return)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Avg Return</p>
                <p className={`text-lg font-semibold ${getReturnColor(history.avg_return)}`}>
                  {formatPercentage(history.avg_return)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Win Rate</p>
                <p className="text-lg font-semibold text-gray-900">
                  {formatPercentage(history.win_rate)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Total Trades</p>
                <p className="text-lg font-semibold text-gray-900">
                  {history.total_trades || 0}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Profitable</p>
                <p className="text-lg font-semibold text-green-600">
                  {history.profitable_trades || 0}
                </p>
              </div>
            </div>

            {/* Time Range and Token Info */}
            <div className="flex flex-wrap gap-4 mb-4 text-sm">
              <div className="flex items-center text-gray-600">
                <span className="font-medium">Period:</span>
                <span className="ml-1">
                  {formatDate(history.time_start)} - {formatDate(history.time_end)}
                </span>
              </div>
              <div className="flex items-center text-gray-600">
                <span className="font-medium">Token:</span>
                <span className="ml-1">{history.token_symbol}</span>
              </div>
              <div className="flex items-center text-gray-600">
                <span className="font-medium">Network:</span>
                <span className="ml-1">{history.network?.toUpperCase()}</span>
              </div>
              <div className="flex items-center text-gray-600">
                <span className="font-medium">Timeframe:</span>
                <span className="ml-1">{history.timeframe}</span>
              </div>
              <div className="flex items-center text-gray-600">
                <span className="font-medium">Data Points:</span>
                <span className="ml-1">{history.data_points}</span>
              </div>
            </div>

            {/* Strategy Details */}
            {history.strategy && (
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-900 mb-3">Strategy Details</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  {/* Filter Signal */}
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <p className="font-medium text-blue-800">Filter Signal</p>
                    <p className="text-blue-700">{history.strategy.filter_condition.signal_name}</p>
                    <p className="text-xs text-blue-600 mt-1">
                      {history.strategy.filter_condition.signal_description}
                    </p>
                  </div>
                  
                  {/* Buy Condition */}
                  <div className="bg-green-50 p-3 rounded-lg">
                    <p className="font-medium text-green-800">Buy Condition</p>
                    <p className="text-green-700">{history.strategy.buy_condition.signal_name}</p>
                    <p className="text-green-600 font-medium">
                      {history.strategy.buy_condition.operator} {history.strategy.buy_condition.threshold}
                    </p>
                    <p className="text-xs text-green-600 mt-1">
                      {history.strategy.buy_condition.signal_description}
                    </p>
                  </div>
                  
                  {/* Sell Condition */}
                  <div className="bg-red-50 p-3 rounded-lg">
                    <p className="font-medium text-red-800">Sell Condition</p>
                    <p className="text-red-700">{history.strategy.sell_condition.signal_name}</p>
                    <p className="text-red-600 font-medium">
                      {history.strategy.sell_condition.operator} {history.strategy.sell_condition.threshold}
                    </p>
                    <p className="text-xs text-red-600 mt-1">
                      {history.strategy.sell_condition.signal_description}
                    </p>
                  </div>
                </div>
                
                {/* Position Info */}
                <div className="flex gap-4 mt-3 text-sm text-gray-600">
                  <div>
                    <span className="font-medium">Position Size:</span>
                    <span className="ml-1">{history.strategy.position_size}</span>
                  </div>
                  <div>
                    <span className="font-medium">Max Position Value:</span>
                    <span className="ml-1">{history.strategy.max_position_value}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default BacktestHistory; 