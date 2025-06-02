import React, { useState, useEffect, useRef } from 'react';
import { useCanvas } from '../../contexts/CanvasContext';
import { usePrivy } from '@privy-io/react-auth';
import WelcomeAnimation from '../common/WelcomeAnimation';
import BacktestResultCard from './BacktestResultCard';

const BacktestResults = ({ lastResults }) => {
  const { authenticated, user } = usePrivy();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeResult, setActiveResult] = useState(null);

  // Process last results when they're updated - only keep the most recent one
  useEffect(() => {
    if (lastResults && lastResults.success) {
      console.log('BacktestResults - Processing lastResults:', lastResults);
      console.log('BacktestResults - backtest_results in lastResults:', lastResults.backtest_results);
      console.log('BacktestResults - signals in lastResults:', lastResults.signals);
      
      const newResult = {
        id: lastResults.strategy_id,
        name: `Strategy ${lastResults.strategy_id}`,
        description: 'Backtest strategy',
        performance: lastResults.performance || {},
        fig: lastResults.fig,
        backtest_results: lastResults.backtest_results,
        signals: lastResults.signals,
        isLiveTrade: false
      };
      
      console.log('BacktestResults - Setting activeResult with signals:', newResult.signals);
      setActiveResult(newResult);
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, [lastResults]);

  // Set initial loading state
  useEffect(() => {
    setLoading(false);
  }, [authenticated, user?.wallet?.address]);

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

  if (!activeResult) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <p className="text-lg mb-2">No backtest results available</p>
          <p className="text-sm">Create a strategy and run a backtest to see results here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full space-y-6 p-4 overflow-y-auto">
      <BacktestResultCard
        result={activeResult}
        resultId={activeResult.id}
      />
    </div>
  );
};

export default BacktestResults; 