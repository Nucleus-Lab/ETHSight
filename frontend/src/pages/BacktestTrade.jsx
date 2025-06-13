import { useState, useEffect } from 'react'
import Navbar from '../components/layout/Navbar'
import BacktestTabContent from '../components/backtest/BacktestTabContent'
import StrategyForm from '../components/backtest/StrategyForm'
import { ChatProvider } from '../contexts/ChatContext'
import { PrivyProvider } from '@privy-io/react-auth';
import { CanvasProvider } from '../contexts/CanvasContext';
import { SubscriptionProvider } from '../contexts/SubscriptionContext';
import { toast } from 'react-hot-toast'; 

function BacktestTrade() {
  const [activeTab, setActiveTab] = useState('results')
  const [activeStrategies, setActiveStrategies] = useState([])
  const [lastResults, setLastResults] = useState(null)
  const [liveTradeData, setLiveTradeData] = useState(null) 
  
  // Log state changes for debugging
  useEffect(() => {
    console.log('BacktestTrade - Active strategies updated:', activeStrategies);
  }, [activeStrategies]);

  console.log('BacktestTrade - Active tab:', activeTab)
  
  const handleStrategySubmit = (result) => {
    console.log('Received result:', result);
    
    if (result.success) {
      // Add the strategy ID to active strategies for display
      if (result.strategy_id) {
        setActiveStrategies(prev => [...prev, result.strategy_id]);
      }
      
      // Store the last results
      setLastResults(result);
      
      // Auto-switch to results tab
      setActiveTab('results');
      
      // Show appropriate notification
      toast.success('Backtest completed successfully!');
    } else {
      // Handle errors
      toast.error(result.message || 'Operation failed. Please try again.');
    }
  };

  const handleLiveTradeStart = (strategy) => {
    console.log('Live trade started with strategy:', strategy);
    
    // Clear backtest results when starting live trade
    setLastResults(null);
    
    // Set live trade data
    setLiveTradeData(strategy);
    
    // Auto-switch to results tab to show live trading
    setActiveTab('results');
    
    // Show notification
    toast.success('Live trading started!');
  };

  const handleLiveTradeStop = () => {
    console.log('handleLiveTradeStop called in BacktestTrade.jsx');
    
    // Clear live trade data
    setLiveTradeData(null);
    
    // Show notification
    toast.success('Live trading stopped!');
    
    console.log('Live trade data cleared, notification shown');
  };

  return (
    <SubscriptionProvider>
      <PrivyProvider
        appId={import.meta.env.VITE_PRIVY_APP_ID}
        config={{
          loginMethods: ['wallet', 'email'],
          appearance: {
            theme: 'light',
            accentColor: '#ffde0f',
          },
        }}
      >
        <CanvasProvider>
          <ChatProvider>
            <div className="fixed inset-0 flex flex-col">
              {/* Navbar */}
              <Navbar />
              
              {/* Main Content */}
              <div className="flex flex-col md:flex-row flex-1 min-h-0">
                {/* Left Side - Strategy Form */}
                <div className="w-[400px] min-w-[400px] border-r overflow-y-auto bg-gray-50">
                  <div className="p-4">
                    <StrategyForm 
                      onSubmit={handleStrategySubmit} 
                      onLiveTradeStart={handleLiveTradeStart}
                      onLiveTradeStop={handleLiveTradeStop}
                    />
                  </div>
                </div>
                
                {/* Right Side - Tab Content */}
                <div className="flex-1 min-w-0">
                  <BacktestTabContent 
                    activeTab={activeTab} 
                    setActiveTab={setActiveTab}
                    activeStrategies={activeStrategies}
                    setActiveStrategies={setActiveStrategies}
                    lastResults={lastResults}
                    onBacktestComplete={handleStrategySubmit}
                    liveTradeData={liveTradeData}
                    onStopLiveTrade={handleLiveTradeStop}
                  />
                </div>
              </div>
            </div>
          </ChatProvider>
        </CanvasProvider>
      </PrivyProvider>
    </SubscriptionProvider>
  )
}

export default BacktestTrade 