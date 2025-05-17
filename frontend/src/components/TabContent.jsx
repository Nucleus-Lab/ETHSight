import React from 'react';
import Canvas from './tabs/Canvas';
import Files from './tabs/Files';
import Signals from './tabs/Signals';
// TODO: check if history is needed
// import History from './tabs/History';
import { useChatContext } from '../contexts/ChatContext';
import { ChatBubbleLeftIcon } from '@heroicons/react/24/outline';

const TabContent = ({ activeTab, setActiveTab, activeVisualizations, setActiveVisualizations }) => {
  const { isChatOpen, setIsChatOpen } = useChatContext();

  console.log('TabContent - Active tab:', activeTab);
  console.log('TabContent - Active visualizations:', activeVisualizations);

  const tabs = [
    { id: 'canvas', label: 'Canvas' },
    { id: 'files', label: 'Files' },
    { id: 'signals', label: 'Signals' },
    // { id: 'history', label: 'History' },
  ];

  const renderContent = () => {
    console.log('TabContent - Rendering content for tab:', activeTab);
    switch (activeTab) {
      case 'canvas':
        console.log('TabContent - Rendering Canvas with visualizations:', activeVisualizations);
        return (
          <div className="h-full overflow-y-auto">
            <Canvas 
              visualizationIds={activeVisualizations} 
              setActiveVisualizations={setActiveVisualizations}
            />
          </div>
        );
      case 'files':
        return <Files />;
      case 'signals':
        return <Signals />;
    //   case 'history':
    //     return <History />;
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

export default TabContent; 