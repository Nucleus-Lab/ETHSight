import React, { useState, useEffect } from 'react';
import { usePrivy } from '@privy-io/react-auth';
import { getUserStrategies, runBacktest } from '../../services/api';
import WelcomeAnimation from '../common/WelcomeAnimation';

const StrategyList = ({ onBacktestComplete }) => {
  const { authenticated, user } = usePrivy();
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [runningBacktests, setRunningBacktests] = useState(new Set());

  // Fetch strategies from backend
  useEffect(() => {
    const fetchStrategies = async () => {
      console.log('StrategyList - Starting to fetch strategies');
      setLoading(true);
      setError(null);
      
      try {
        if (authenticated && user?.wallet?.address) {
          console.log('Fetching strategies for wallet:', user.wallet.address);
          const userStrategies = await getUserStrategies(user.wallet.address);
          console.log('Fetched strategies:', userStrategies);
          setStrategies(userStrategies);
        } else {
          setStrategies([]);
        }
      } catch (error) {
        console.error('StrategyList - Error fetching strategies:', error);
        setError('Failed to load strategies. Please try again.');
        setStrategies([]);
      } finally {
        setLoading(false);
      }
    };

      fetchStrategies();
  }, [authenticated, user?.wallet?.address]);

  const handleRunBacktest = async (strategy) => {
    if (!user?.wallet?.address) {
      console.error('No wallet address available');
      return;
    }

    console.log(`Running backtest for strategy ${strategy.strategy_id}`);
    
    // Mark this strategy as running
    setRunningBacktests(prev => new Set([...prev, strategy.strategy_id]));
    
    try {
      // Create strategy object for API call
      const strategyRequest = {
        filterSignal_id: strategy.filter_condition.signal_id,
        buyCondition: {
          signal_id: strategy.buy_condition.signal_id,
          operator: strategy.buy_condition.operator,
          threshold: parseFloat(strategy.buy_condition.threshold)
        },
        sellCondition: {
          signal_id: strategy.sell_condition.signal_id,
          operator: strategy.sell_condition.operator,
          threshold: parseFloat(strategy.sell_condition.threshold)
        },
        positionSize: parseFloat(strategy.position_size),
        maxPositionValue: parseFloat(strategy.max_position_value),
        timeRange: {
          start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days ago
          end: new Date().toISOString()
        },
        wallet_address: user.wallet.address
      };

      console.log('Sending backtest request:', strategyRequest);
      
      // Run the actual backtest
      const result = await runBacktest(strategyRequest);
      
      console.log('Backtest completed:', result);
      
      // Notify parent component of completion
      if (onBacktestComplete) {
        onBacktestComplete(result);
      }
      
    } catch (error) {
      console.error(`Error running backtest for strategy ${strategy.strategy_id}:`, error);
      // You could show an error toast here
    } finally {
      // Remove from running set
      setRunningBacktests(prev => {
        const newSet = new Set(prev);
        newSet.delete(strategy.strategy_id);
        return newSet;
      });
    }
  };

  const formatCondition = (condition) => {
    if (!condition) return 'N/A';
    
    if (condition.operator && condition.threshold != null) {
      return `${condition.signal_name} ${condition.operator} ${condition.threshold}`;
    }
    
    return condition.signal_name || 'N/A';
  };

  const truncateText = (text, maxLength = 60) => {
    if (!text) return 'N/A';
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  if (!authenticated) {
    return <WelcomeAnimation />;
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center text-red-500">
        {error}
      </div>
    );
  }

  if (strategies.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <p className="text-lg mb-2">No strategies found</p>
          <p className="text-sm">Create your first strategy to get started.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-4">
      {strategies.map((strategy) => (
        <div 
          key={`strategy-${strategy.strategy_id}`}
          className="bg-white p-4 rounded-lg shadow-md border border-gray-200 hover:shadow-lg transition-shadow"
        >
          <div className="flex justify-between items-start mb-3">
            <h3 className="text-lg font-semibold text-gray-800">
              Strategy #{strategy.strategy_id}
            </h3>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {new Date(strategy.created_at).toLocaleDateString()}
            </span>
          </div>
          
          {/* Position Information */}
          <div className="mb-4 p-3 bg-gray-50 rounded-md">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-600">Position Size:</span>
                <p className="font-medium">{strategy.position_size} ETH</p>
              </div>
              <div>
                <span className="text-gray-600">Max Value:</span>
                <p className="font-medium">${strategy.max_position_value}</p>
              </div>
            </div>
          </div>

          {/* Filter Condition */}
          <div className="mb-3">
            <div className="text-xs font-medium text-gray-700 mb-1">FILTER CONDITION</div>
            <div className="text-sm bg-blue-50 p-2 rounded border-l-3 border-blue-400">
              <div className="font-medium text-blue-900">{strategy.filter_condition?.signal_name || 'N/A'}</div>
              <div className="text-blue-700 text-xs mt-1">
                {truncateText(strategy.filter_condition?.signal_description)}
              </div>
            </div>
          </div>

          {/* Buy Condition */}
          <div className="mb-3">
            <div className="text-xs font-medium text-gray-700 mb-1">BUY CONDITION</div>
            <div className="text-sm bg-green-50 p-2 rounded border-l-3 border-green-400">
              <div className="font-medium text-green-900">
                {formatCondition(strategy.buy_condition)}
              </div>
              <div className="text-green-700 text-xs mt-1">
                {truncateText(strategy.buy_condition?.signal_description)}
              </div>
            </div>
          </div>

          {/* Sell Condition */}
          <div className="mb-4">
            <div className="text-xs font-medium text-gray-700 mb-1">SELL CONDITION</div>
            <div className="text-sm bg-red-50 p-2 rounded border-l-3 border-red-400">
              <div className="font-medium text-red-900">
                {formatCondition(strategy.sell_condition)}
              </div>
              <div className="text-red-700 text-xs mt-1">
                {truncateText(strategy.sell_condition?.signal_description)}
              </div>
            </div>
          </div>
          
          {/* Action Button */}
          <div className="flex justify-end">
            <button
              onClick={() => handleRunBacktest(strategy)}
              disabled={runningBacktests.has(strategy.strategy_id)}
              className={`px-4 py-2 rounded transition-colors ${
                runningBacktests.has(strategy.strategy_id)
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-primary-main text-black hover:bg-primary-hover'
              }`}
            >
              {runningBacktests.has(strategy.strategy_id) ? (
                <div className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Running...
                </div>
              ) : (
                'Run Backtest'
              )}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default StrategyList; 