import { useState, useEffect } from 'react'
import Navbar from '../components/layout/Navbar'
import ChatInterface from '../components/layout/ChatInterface'
import BacktestTabContent from '../components/backtest/BacktestTabContent'
import { ChatProvider } from '../contexts/ChatContext'
import ChatToggleButton from '../components/layout/ChatToggleButton'
import { PrivyProvider } from '@privy-io/react-auth';
import { CanvasProvider } from '../contexts/CanvasContext';
import { SubscriptionProvider } from '../contexts/SubscriptionContext';

function BacktestTrade() {
  const [activeTab, setActiveTab] = useState('results')
  const [activeStrategies, setActiveStrategies] = useState([])
  
  // Log state changes for debugging
  useEffect(() => {
    console.log('BacktestTrade - Active strategies updated:', activeStrategies);
  }, [activeStrategies]);

  console.log('BacktestTrade - Active tab:', activeTab)

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
                <ChatInterface 
                  setActiveTab={setActiveTab}
                  setActiveVisualizations={setActiveStrategies}
                />
                {/* Right Side - Tab Content */}
                <div className="flex-1 min-w-0">
                  <BacktestTabContent 
                    activeTab={activeTab} 
                    setActiveTab={setActiveTab}
                    activeStrategies={activeStrategies}
                    setActiveStrategies={setActiveStrategies}
                  />
                </div>
              </div>

              {/* Mobile Chat Toggle Button - Fixed at bottom right on mobile */}
              <div className="md:hidden">
                <ChatToggleButton />
              </div>
            </div>
          </ChatProvider>
        </CanvasProvider>
      </PrivyProvider>
    </SubscriptionProvider>
  )
}

export default BacktestTrade 