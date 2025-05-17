import React, { useState, useEffect, useRef } from 'react';
import { useCanvas } from '../../contexts/CanvasContext';
import { usePrivy } from '@privy-io/react-auth';
import WelcomeAnimation from '../common/WelcomeAnimation';
import BacktestResultCard from './BacktestResultCard';

const BacktestResults = ({ strategyIds = [], setActiveStrategies }) => {
  const { currentCanvasId } = useCanvas();
  const { authenticated, user } = usePrivy();
  const [backtestResults, setBacktestResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const resultRefs = useRef({});

  // Add auto-scroll effect for new results
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [backtestResults]);

  // Fetch backtest results (to be implemented)
  useEffect(() => {
    const fetchBacktestResults = async () => {
      console.log('BacktestResults - Starting to fetch results');
      setLoading(true);
      setError(null);
      
      try {
        // This will be implemented to fetch actual strategies
        // For now, just creating placeholder data
        if (strategyIds && strategyIds.length > 0) {
          // Placeholder data - will be replaced with actual API calls
          const dummyResults = strategyIds.map(id => ({
            id,
            name: `Strategy ${id}`,
            description: `This is a description for strategy ${id}`,
            performance: {
              totalReturn: Math.random() * 100,
              sharpeRatio: (Math.random() * 3).toFixed(2),
              drawdown: (Math.random() * 30).toFixed(2),
            },
            data: {
              // Placeholder chart data
              x: Array.from({ length: 30 }, (_, i) => new Date(2023, 0, i + 1).toISOString()),
              y: Array.from({ length: 30 }, () => 1000 + Math.random() * 500),
              type: 'scatter',
              mode: 'lines',
              name: 'Portfolio Value'
            }
          }));
          
          setBacktestResults(dummyResults);
        } else {
          setBacktestResults([]);
        }
      } catch (error) {
        console.error('BacktestResults - Error fetching results:', error);
        setError('Failed to load backtest results');
      } finally {
        setLoading(false);
      }
    };

    if (authenticated && user?.wallet?.address) {
      fetchBacktestResults();
    } else {
      setLoading(false);
      setBacktestResults([]);
    }
  }, [strategyIds, authenticated, user?.wallet?.address]);

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

  if (backtestResults.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        No backtest results available. Try running a backtest first.
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full space-y-6 p-4 overflow-y-auto relative">
      {backtestResults.map((result, index) => (
        <div 
          key={`result-${result.id || index}`}
          ref={resultRefs.current[result.id] || null}
        >
          <BacktestResultCard
            result={result}
            resultId={result.id}
          />
        </div>
      ))}
      <div ref={bottomRef} /> {/* Add ref for auto-scrolling */}
    </div>
  );
};

export default BacktestResults; 