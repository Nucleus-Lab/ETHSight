import React, { useState, useEffect, useRef } from 'react';
import { useCanvas } from '../../contexts/CanvasContext';
import { usePrivy } from '@privy-io/react-auth';
import WelcomeAnimation from '../common/WelcomeAnimation';
import BacktestResultCard from './BacktestResultCard';

const BacktestResults = ({ strategyIds = [], setActiveStrategies, lastResults }) => {
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

  // Process last results when they're updated
  useEffect(() => {
    if (lastResults && lastResults.success) {
      // Check if this result is already in backtestResults
      const existingIndex = backtestResults.findIndex(result => result.id === lastResults.strategy_id);
      
      const newResult = {
        id: lastResults.strategy_id,
        name: `Strategy ${lastResults.strategy_id}`,
        description: lastResults.strategy_id.startsWith('trade_') 
          ? 'Live trading strategy' 
          : 'Backtest strategy',
        performance: lastResults.performance || {},
        fig: lastResults.fig,
        signals: lastResults.signals,
        isLiveTrade: lastResults.strategy_id.startsWith('trade_')
      };
      
      if (existingIndex >= 0) {
        // Update existing result
        setBacktestResults(prev => {
          const updated = [...prev];
          updated[existingIndex] = newResult;
          return updated;
        });
      } else {
        // Add new result
        setBacktestResults(prev => [...prev, newResult]);
      }
    }
  }, [lastResults]);

  // Format chart data from backend to format needed by Plotly
  const formatChartData = (chartData) => {
    if (!chartData) return null;
    
    // For live trade which might not have chart data yet
    if (chartData.message) return null;
    
    return {
      x: chartData.dates,
      y: chartData.portfolio_values,
      type: 'scatter',
      mode: 'lines',
      name: 'Portfolio Value',
      tradePoints: chartData.trade_points
    };
  };

  // Fetch backtest results (to be implemented)
  useEffect(() => {
    const fetchBacktestResults = async () => {
      console.log('BacktestResults - Starting to fetch results for strategyIds:', strategyIds);
      
      if (!strategyIds || strategyIds.length === 0) {
        setLoading(false);
        return;
      }
      
      setLoading(true);
      setError(null);
      
      try {
        // For now, results are handled via lastResults prop for new strategies
        // This effect would be used for loading historical results
        
        // Instead, filter any strategies that don't have results yet
        const missingStrategies = strategyIds.filter(id => 
          !backtestResults.some(result => result.id === id) && 
          (!lastResults || lastResults.strategy_id !== id)
        );
        
        if (missingStrategies.length > 0) {
          // This would be replaced with an actual API call in a real implementation
          console.log('BacktestResults - Would fetch these missing strategies:', missingStrategies);
          
          // For demo, create placeholder data - in real app, we'd fetch from backend
          const placeholderResults = missingStrategies.map(id => ({
            id,
            name: `Strategy ${id}`,
            description: id.startsWith('trade_') ? 'Live trading strategy' : 'Backtest strategy',
            performance: {
              totalReturn: Math.random() * 100 - 20, // -20% to +100%
              sharpeRatio: (Math.random() * 3).toFixed(2),
              maxDrawdown: (Math.random() * 30).toFixed(2),
              winRate: (Math.random() * 50 + 30).toFixed(2), // 30% to 80%
              trades: Math.floor(Math.random() * 50 + 10), // 10 to 60 trades
            },
            data: {
              x: Array.from({ length: 30 }, (_, i) => new Date(2023, 0, i + 1).toISOString()),
              y: Array.from({ length: 30 }, (_, i) => 10000 * (1 + (Math.random() * 0.5 - 0.1) * (i / 30))),
              type: 'scatter',
              mode: 'lines',
              name: 'Portfolio Value'
            },
            isLiveTrade: id.startsWith('trade_')
          }));
          
          setBacktestResults(prev => [...prev, ...placeholderResults]);
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
  }, [strategyIds, authenticated, user?.wallet?.address, lastResults]);

  if (!authenticated) {
    return <WelcomeAnimation />;
  }

  if (loading && backtestResults.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error && backtestResults.length === 0) {
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
      {loading && (
        <div className="py-4 flex justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      )}
      <div ref={bottomRef} /> {/* Add ref for auto-scrolling */}
    </div>
  );
};

export default BacktestResults; 