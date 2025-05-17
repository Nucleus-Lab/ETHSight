import React from 'react';
import { useChatContext } from '../../contexts/ChatContext';
import { ChatBubbleLeftIcon, XMarkIcon } from '@heroicons/react/24/outline';

const ChatToggleButton = () => {
  const { isChatOpen, setIsChatOpen } = useChatContext();

  return (
    <button
      onClick={() => setIsChatOpen(!isChatOpen)}
      className="fixed bottom-4 right-4 p-3 bg-primary-main text-black rounded-full shadow-lg hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary-main focus:ring-offset-2"
    >
      {isChatOpen ? (
        <XMarkIcon className="h-6 w-6" />
      ) : (
        <ChatBubbleLeftIcon className="h-6 w-6" />
      )}
    </button>
  );
};

export default ChatToggleButton; 