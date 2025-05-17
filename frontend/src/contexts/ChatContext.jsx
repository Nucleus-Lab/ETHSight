import React, { createContext, useContext, useState } from 'react';

const ChatContext = createContext();

export function ChatProvider({ children }) {
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [chatInputText, setChatInputText] = useState('');

  return (
    <ChatContext.Provider value={{ 
      isChatOpen, 
      setIsChatOpen,
      chatInputText,
      setChatInputText
    }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  return useContext(ChatContext);
} 