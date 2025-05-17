import React, { useState, useEffect } from 'react';
import { usePrivy } from '@privy-io/react-auth';
import WelcomeAnimation from '../common/WelcomeAnimation';

const StrategyList = ({ setActiveStrategies }) => {
  const { authenticated, user } = usePrivy();
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch strategies (to be implemented)
  useEffect(() => {
    const fetchStrategies = async () => {
      console.log('StrategyList - Starting to fetch strategies');
      setLoading(true);
      setError(null);
      
      try {
        // This will be implemented to fetch actual strategies
        // For now, just creating placeholder data
        const dummyStrategies = [
          {
            id: 1,
            name: 'Mean Reversion ETH/USDT',
            description: 'A strategy that buys ETH when price is below the 20-day moving average and sells when above.',
            tags: ['mean-reversion', 'ethereum', 'technical'],
            created_at: '2023-06-15T10:30:00Z',
          },
          {
            id: 2,
            name: 'Momentum BTC/USDT',
            description: 'Captures upward trends in Bitcoin by buying when short-term momentum indicators turn positive.',
            tags: ['momentum', 'bitcoin', 'technical'],
            created_at: '2023-07-22T14:15:00Z',
          },
          {
            id: 3,
            name: 'EMA Crossover Strategy',
            description: 'Uses exponential moving average crossovers to determine entry and exit points.',
            tags: ['ema', 'crossover', 'trend-following'],
            created_at: '2023-08-05T09:45:00Z',
          },
        ];
        
        setStrategies(dummyStrategies);
      } catch (error) {
        console.error('StrategyList - Error fetching strategies:', error);
        setError('Failed to load strategies');
      } finally {
        setLoading(false);
      }
    };

    if (authenticated && user?.wallet?.address) {
      fetchStrategies();
    } else {
      setLoading(false);
      setStrategies([]);
    }
  }, [authenticated, user?.wallet?.address]);

  const handleRunBacktest = (strategyId) => {
    console.log(`Running backtest for strategy ${strategyId}`);
    // Add strategy to active strategies
    setActiveStrategies(prev => {
      if (prev.includes(strategyId)) {
        return prev;
      }
      return [...prev, strategyId];
    });
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
        No strategies available. Create a strategy first.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-4">
      {strategies.map((strategy) => (
        <div 
          key={`strategy-${strategy.id}`}
          className="bg-white p-4 rounded-lg shadow-md border border-gray-200 hover:shadow-lg transition-shadow"
        >
          <h3 className="text-lg font-semibold mb-2">{strategy.name}</h3>
          <p className="text-gray-600 mb-4">{strategy.description}</p>
          
          <div className="flex flex-wrap gap-2 mb-4">
            {strategy.tags.map((tag, index) => (
              <span 
                key={index} 
                className="bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-500">
              Created: {new Date(strategy.created_at).toLocaleDateString()}
            </span>
            <button
              onClick={() => handleRunBacktest(strategy.id)}
              className="px-4 py-2 bg-primary-main text-black rounded hover:bg-primary-hover transition-colors"
            >
              Run Backtest
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default StrategyList; 