import React, { useState, useEffect } from 'react';
import { usePrivy } from '@privy-io/react-auth';
import DatePicker from 'react-datepicker';
import { Switch } from '@headlessui/react';
import 'react-datepicker/dist/react-datepicker.css';
import { getAllSignalsForUser, runBacktest, executeTrade, getUserStrategies, getStrategyById } from '../../services/api';
import LiveTradeResults from './LiveTradeResults';

// Add these constants at the top of the file after imports
const NETWORKS = [
  { value: 'eth', label: 'Ethereum' },
  { value: 'bsc', label: 'BSC' }
];

const TIMEFRAMES = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' }
];

const StrategyForm = ({ onSubmit }) => {
  const { authenticated, user } = usePrivy();
  const [loading, setLoading] = useState(false);
  const [signals, setSignals] = useState([]);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [signalError, setSignalError] = useState(null);
  
  // Mode toggle (backtest or trade)
  const [isTradeMode, setIsTradeMode] = useState(false);
  
  // Form state
  const [filterSignal, setFilterSignal] = useState('');
  
  const [buySignal, setBuySignal] = useState('');
  const [buyOperator, setBuyOperator] = useState('>');
  const [buyThreshold, setBuyThreshold] = useState(0);
  
  const [sellSignal, setSellSignal] = useState('');
  const [sellOperator, setSellOperator] = useState('<');
  const [sellThreshold, setSellThreshold] = useState(0);
  
  const [positionSize, setPositionSize] = useState(1);
  const [maxPositionValue, setMaxPositionValue] = useState(10000);
  
  // Add new state for network and timeframe
  const [network, setNetwork] = useState('eth');
  const [timeframe, setTimeframe] = useState('1d');
  
  const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));
  const [endDate, setEndDate] = useState(new Date());
  
  // Add new state for live trading
  const [isLiveTrading, setIsLiveTrading] = useState(false);
  
  // Add new state for current strategy
  const [currentStrategy, setCurrentStrategy] = useState(null);
  
  // Add new state for strategies list and selected strategy
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [loadingStrategies, setLoadingStrategies] = useState(false);
  
  // Fetch signals from API
  useEffect(() => {
    const fetchSignals = async () => {
      // Only fetch if user is authenticated and has a wallet
      if (!authenticated || !user?.wallet?.address) {
        return;
      }
      
      setLoadingSignals(true);
      setSignalError(null);
      
      try {
        console.log('Fetching signals for wallet:', user.wallet.address);
        const userSignals = await getAllSignalsForUser(user.wallet.address);
        console.log('Fetched signals:', userSignals);
        
        if (Array.isArray(userSignals)) {
          setSignals(userSignals);
        } else {
          console.error('Expected array of signals, got:', typeof userSignals);
          setSignals([]);
        }
      } catch (error) {
        console.error('Error fetching signals:', error);
        setSignalError('Failed to load signals. Please try again.');
        
        // Fallback to empty signals array
        setSignals([]);
      } finally {
        setLoadingSignals(false);
      }
    };
    
    fetchSignals();
  }, [authenticated, user?.wallet?.address]);
  
  // Fetch user's strategies
  useEffect(() => {
    const fetchStrategies = async () => {
      if (!authenticated || !user?.wallet?.address) return;
      
      setLoadingStrategies(true);
      try {
        const userStrategies = await getUserStrategies(user.wallet.address);
        setStrategies(userStrategies);
      } catch (error) {
        console.error('Error fetching strategies:', error);
      } finally {
        setLoadingStrategies(false);
      }
    };
    
    fetchStrategies();
  }, [authenticated, user?.wallet?.address]);
  
  // Fetch strategy details when one is selected
  useEffect(() => {
    const fetchStrategyDetails = async () => {
      if (!selectedStrategyId) {
        setSelectedStrategy(null);
        return;
      }
      
      try {
        const strategy = await getStrategyById(selectedStrategyId);
        setSelectedStrategy(strategy);
      } catch (error) {
        console.error('Error fetching strategy details:', error);
      }
    };
    
    fetchStrategyDetails();
  }, [selectedStrategyId]);
  
  const operators = ['=', '>', '<', '>=', '<='];
  
  // Helper function to format signal names
  const formatSignalName = (signal) => {
    if (!signal) return '';
    
    // If signal has a signal_name property (from backend), use it
    if (signal.signal_name) {
      return signal.signal_name;
    }
    
    // If signal has a name property (legacy support)
    if (signal.name) {
      return signal.name;
    }
    
    // If no name but has signal_definition, create a readable name
    if (signal.signal_definition) {
      // Clean up and shorten the definition for display
      const cleanDefinition = signal.signal_definition
        .replace(/^Generate a signal that/, '')
        .replace(/^Create a signal that/, '')
        .trim();
      return cleanDefinition.length > 50 ? `${cleanDefinition.substring(0, 47)}...` : cleanDefinition;
    }
    
    // Last resort: use signal ID
    return `Signal #${signal.signal_id}`;
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!authenticated || !user?.wallet?.address) {
      return;
    }
    
    setLoading(true);
    
    try {
      if (isTradeMode) {
        if (!selectedStrategyId) {
          throw new Error('No strategy selected');
        }
        
        // Store strategy ID and start live trading
        setCurrentStrategy({
          strategy_id: selectedStrategyId,
          network,
          timeframe
        });
        setIsLiveTrading(true);
      } else {
        // Backtest logic with updated format
        const strategy = {
          filter_signal_id: parseInt(filterSignal),
          buy_signal_id: parseInt(buySignal),
          buy_operator: buyOperator,
          buy_threshold: parseFloat(buyThreshold),
          sell_signal_id: parseInt(sellSignal),
          sell_operator: sellOperator,
          sell_threshold: parseFloat(sellThreshold),
          position_size: parseFloat(positionSize),
          max_position_value: parseFloat(maxPositionValue),
          time_range: {
            start: startDate.toISOString(),
            end: endDate.toISOString()
          },
          wallet_address: user.wallet.address,
          network,
          timeframe
        };
        
        const result = await runBacktest(strategy);
        if (onSubmit) {
          onSubmit(result);
        }
      }
    } catch (error) {
      console.error(`Error during ${isTradeMode ? 'trade' : 'backtest'}:`, error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleStopTrading = () => {
    setIsLiveTrading(false);
    setIsTradeMode(false);
    setCurrentStrategy(null);
  };
  
  // Add function to fetch strategies
  const fetchStrategies = async () => {
    if (!authenticated || !user?.wallet?.address) return;
    
    setLoadingStrategies(true);
    try {
      const userStrategies = await getUserStrategies(user.wallet.address);
      setStrategies(userStrategies);
    } catch (error) {
      console.error('Error fetching strategies:', error);
    } finally {
      setLoadingStrategies(false);
    }
  };

  // Update strategies when trade mode is toggled
  useEffect(() => {
    if (isTradeMode) {
      fetchStrategies();
    }
  }, [isTradeMode, authenticated, user?.wallet?.address]);
  
  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white rounded-lg shadow">
      {isLiveTrading && currentStrategy ? (
        <LiveTradeResults 
          onStop={handleStopTrading} 
          strategy={currentStrategy} 
        />
      ) : (
        <>
          {/* Mode Toggle */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-800">
              {isTradeMode ? "Execute Trade" : "Backtest"}
            </h2>
            <div className="flex items-center">
              <span className={`mr-2 text-sm ${!isTradeMode ? 'font-medium text-gray-700' : 'text-gray-500'}`}>
                Backtest
              </span>
              <Switch
                checked={isTradeMode}
                onChange={setIsTradeMode}
                className={`${
                  isTradeMode ? 'bg-primary-main' : 'bg-gray-300'
                } relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-main focus:ring-offset-2`}
              >
                <span
                  className={`${
                    isTradeMode ? 'translate-x-6' : 'translate-x-1'
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                />
              </Switch>
              <span className={`ml-2 text-sm ${isTradeMode ? 'font-medium text-gray-700' : 'text-gray-500'}`}>
                Trade
              </span>
            </div>
          </div>
          
          {loadingSignals && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 text-blue-800 rounded-md text-sm flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Loading your signals...
            </div>
          )}
          
          {signalError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-800 rounded-md text-sm">
              {signalError}
            </div>
          )}
          
          {!loadingSignals && signals.length === 0 && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-md text-sm">
              No signals found. Please create signals in the Analytics page first.
            </div>
          )}
          
          {isTradeMode && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-800 rounded-md text-sm">
              <div className="font-semibold mb-1">Warning: Trade mode</div>
              <div>You are about to execute real trades. This will use actual funds from your wallet.</div>
            </div>
          )}
          
          {isTradeMode ? (
            // Trade Mode Form
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Strategy Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select Strategy
                </label>
                {loadingStrategies ? (
                  <div className="flex items-center space-x-2 text-sm text-gray-500">
                    <svg className="animate-spin h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Loading strategies...</span>
                  </div>
                ) : (
                  <select
                    value={selectedStrategyId}
                    onChange={(e) => setSelectedStrategyId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                  >
                    <option value="">Select a strategy</option>
                    {strategies.map(strategy => (
                      <option key={strategy.strategy_id} value={strategy.strategy_id}>
                        Strategy #{strategy.strategy_id} - {new Date(strategy.created_at).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                )}
                {strategies.length === 0 && !loadingStrategies && (
                  <p className="mt-1 text-sm text-gray-500">
                    No strategies found. Create a strategy by running a backtest first.
                  </p>
                )}
              </div>
              
              {/* Strategy Preview */}
              {selectedStrategy && (
                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Strategy Preview</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">Filter Signal: </span>
                      {selectedStrategy.filterSignal.signal_name}
                    </div>
                    <div>
                      <span className="font-medium">Buy Condition: </span>
                      {selectedStrategy.buyCondition.signal_name} {selectedStrategy.buyCondition.operator} {selectedStrategy.buyCondition.threshold}
                    </div>
                    <div>
                      <span className="font-medium">Sell Condition: </span>
                      {selectedStrategy.sellCondition.signal_name} {selectedStrategy.sellCondition.operator} {selectedStrategy.sellCondition.threshold}
                    </div>
                    <div>
                      <span className="font-medium">Position Size: </span>
                      {selectedStrategy.positionSize} ETH
                    </div>
                    <div>
                      <span className="font-medium">Max Position Value: </span>
                      ${selectedStrategy.maxPositionValue}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Network and Timeframe Selection */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Network
                  </label>
                  <select
                    value={network}
                    onChange={(e) => setNetwork(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                  >
                    {NETWORKS.map(({ value, label }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Timeframe
                  </label>
                  <select
                    value={timeframe}
                    onChange={(e) => setTimeframe(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                  >
                    {TIMEFRAMES.map(({ value, label }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading || !authenticated || !selectedStrategy}
                className="w-full py-3 px-4 bg-red-500 text-white font-medium rounded-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {loading ? 'Executing Trade...' : 'Execute Trade'}
              </button>
            </form>
          ) : (
            // Backtest Mode Form - Keep existing form code
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Token Filtering Condition */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Token Filtering Condition
                </label>
                <select
                  value={filterSignal}
                  onChange={(e) => setFilterSignal(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                  required
                  disabled={loadingSignals || signals.length === 0}
                >
                  <option value="">Select a signal</option>
                  {signals.map(signal => (
                    <option key={signal.signal_id} value={signal.signal_id}>
                      {formatSignalName(signal)}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Select a signal to filter which tokens to trade
                </p>
              </div>
              
              {/* Buy Condition */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Buy Condition
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <select
                    value={buySignal}
                    onChange={(e) => setBuySignal(e.target.value)}
                    className="col-span-3 sm:col-span-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                    disabled={loadingSignals || signals.length === 0}
                  >
                    <option value="">Select signal</option>
                    {signals.map(signal => (
                      <option key={signal.signal_id} value={signal.signal_id}>
                        {formatSignalName(signal)}
                      </option>
                    ))}
                  </select>
                  
                  <select
                    value={buyOperator}
                    onChange={(e) => setBuyOperator(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                    disabled={signals.length === 0}
                  >
                    {operators.map(op => (
                      <option key={op} value={op}>{op}</option>
                    ))}
                  </select>
                  
                  <input
                    type="number"
                    value={buyThreshold}
                    onChange={(e) => setBuyThreshold(parseFloat(e.target.value))}
                    className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    placeholder="Threshold"
                    required
                    disabled={signals.length === 0}
                  />
                </div>
              </div>
              
              {/* Sell Condition */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Sell Condition
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <select
                    value={sellSignal}
                    onChange={(e) => setSellSignal(e.target.value)}
                    className="col-span-3 sm:col-span-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                    disabled={loadingSignals || signals.length === 0}
                  >
                    <option value="">Select signal</option>
                    {signals.map(signal => (
                      <option key={signal.signal_id} value={signal.signal_id}>
                        {formatSignalName(signal)}
                      </option>
                    ))}
                  </select>
                  
                  <select
                    value={sellOperator}
                    onChange={(e) => setSellOperator(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                    disabled={signals.length === 0}
                  >
                    {operators.map(op => (
                      <option key={op} value={op}>{op}</option>
                    ))}
                  </select>
                  
                  <input
                    type="number"
                    value={sellThreshold}
                    onChange={(e) => setSellThreshold(parseFloat(e.target.value))}
                    className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    placeholder="Threshold"
                    required
                    disabled={signals.length === 0}
                  />
                </div>
              </div>
              
              {/* Position Sizing */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Position Size (ETH)
                  </label>
                  <input
                    type="number"
                    value={positionSize}
                    onChange={(e) => setPositionSize(parseFloat(e.target.value))}
                    min="0.01"
                    step="0.01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                    disabled={signals.length === 0}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Position Value (USD)
                  </label>
                  <input
                    type="number"
                    value={maxPositionValue}
                    onChange={(e) => setMaxPositionValue(parseFloat(e.target.value))}
                    min="100"
                    step="100"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                    required
                    disabled={signals.length === 0}
                  />
                </div>
              </div>
              
              {/* Time Range - Only show for backtest mode */}
              {!isTradeMode && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Backtest Time Range
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                      <DatePicker
                        selected={startDate}
                        onChange={date => setStartDate(date)}
                        selectsStart
                        startDate={startDate}
                        endDate={endDate}
                        maxDate={endDate}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                        disabled={signals.length === 0}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">End Date</label>
                      <DatePicker
                        selected={endDate}
                        onChange={date => setEndDate(date)}
                        selectsEnd
                        startDate={startDate}
                        endDate={endDate}
                        minDate={startDate}
                        maxDate={new Date()}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-main focus:border-primary-main"
                        disabled={signals.length === 0}
                      />
                    </div>
                  </div>
                </div>
              )}
              
              {/* Submit Button */}
              <div>
                <button
                  type="submit"
                  disabled={loading || !authenticated || signals.length === 0 || loadingSignals}
                  className={`w-full py-3 px-4 font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-main disabled:bg-gray-300 disabled:cursor-not-allowed ${
                    isTradeMode 
                      ? 'bg-red-500 hover:bg-red-600 text-white focus:ring-red-500' 
                      : 'bg-primary-main hover:bg-primary-hover text-black focus:ring-primary-main'
                  }`}
                >
                  {loading 
                    ? (isTradeMode ? 'Executing Trade...' : 'Running Backtest...') 
                    : loadingSignals 
                      ? 'Loading Signals...' 
                      : (isTradeMode ? 'Execute Trade' : 'Run Backtest')
                  }
                </button>
              </div>
            </form>
          )}
          
          {!authenticated && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-md text-sm">
              Please connect your wallet to create and run backtests.
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default StrategyForm; 