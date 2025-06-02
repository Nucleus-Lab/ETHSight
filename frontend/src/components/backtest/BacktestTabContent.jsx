import React from 'react';
import BacktestResults from './BacktestResults';
import StrategyList from './StrategyList';
import { useChatContext } from '../../contexts/ChatContext';
import { ChatBubbleLeftIcon } from '@heroicons/react/24/outline';

const BacktestTabContent = ({ activeTab, setActiveTab, activeStrategies, setActiveStrategies, lastResults = null, onBacktestComplete }) => {
  const { isChatOpen, setIsChatOpen } = useChatContext();

  console.log('BacktestTabContent - Active tab:', activeTab);
  console.log('BacktestTabContent - Active strategies:', activeStrategies);
  console.log('BacktestTabContent - Last results:', lastResults);

  const tabs = [
    { id: 'results', label: 'Results' },
    { id: 'strategies', label: 'Strategies' },
  ];

  const renderContent = () => {
    console.log('BacktestTabContent - Rendering content for tab:', activeTab);
    switch (activeTab) {
      case 'results':
        console.log('BacktestTabContent - Rendering Results with strategies:', activeStrategies);
        return (
          <div className="h-full overflow-y-auto">
            <BacktestResults 
              lastResults={lastResults}
            />
          </div>
        );
      case 'strategies':
        return (
          <StrategyList 
            onBacktestComplete={onBacktestComplete}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="bg-white">
        <div className="flex items-center">
          {/* Chat toggle button for tablet view */}
          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            className="hidden md:block lg:hidden p-2 mx-2 hover:bg-gray-100 rounded-full"
          >
            <ChatBubbleLeftIcon className="h-6 w-6" />
          </button>

          {/* Tabs */}
          <div className="flex overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'text-gray-700 border-b-2 border-primary-main'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="flex-1 p-4 overflow-auto">
        {renderContent()}
      </div>
    </div>
  );
};

export default BacktestTabContent; 