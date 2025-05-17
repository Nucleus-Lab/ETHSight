import React, { useState, useRef, useEffect } from 'react';
import { useChatContext } from '../../contexts/ChatContext';
import { useCanvas } from '../../contexts/CanvasContext';
import { usePrivy } from '@privy-io/react-auth';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { sendMessage, getCanvasMessages, getMessage } from '../../services/api';
import Message from '../chat/Message';
import PropTypes from 'prop-types';
import { AI_USER_ID } from '../../constants/constants';
import MCPSelector from '../MCPSelector';

const ChatInterface = ({ setActiveTab, setActiveVisualizations }) => {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const { isChatOpen, setIsChatOpen, chatInputText, setChatInputText } = useChatContext();
  const { currentCanvasId, setCurrentCanvasId, clearCanvas } = useCanvas();
  const { ready, authenticated, user, login } = usePrivy();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  console.log('Current canvas ID:', currentCanvasId);

  // Auto scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load messages when canvas changes
  useEffect(() => {
    const loadMessages = async () => {
      if (currentCanvasId) {
        setIsLoadingHistory(true);
        try {
          const history = await getCanvasMessages(currentCanvasId);
          console.log('Message history:', history);
          // for the first message, log the data type of the user_id
          console.log('First message user_id:', history[0].user_id);
          console.log('First message user_id type:', typeof history[0].user_id);
          console.log('AI_USER_ID:', AI_USER_ID);
          console.log('AI_USER_ID type:', typeof AI_USER_ID);
          setMessages(history.map(msg => ({
            id: msg.message_id,
            text: msg.text,
            isUser: parseInt(msg.user_id) !== AI_USER_ID, // Check if the message is from AI
            timestamp: msg.created_at
          })));
        } catch (error) {
          console.error('Failed to load messages:', error);
        } finally {
          setIsLoadingHistory(false);
        }
      } else {
        setMessages([]); // Clear messages when no canvas is selected
      }
    };

    loadMessages();
  }, [currentCanvasId]);

  // Clear messages and canvas when authentication changes
  useEffect(() => {
    if (!authenticated) {
      setMessages([]);
      clearCanvas();
    }
  }, [authenticated, clearCanvas]);

  // Sync the chatInputText from context to the local state
  useEffect(() => {
    if (chatInputText !== message) {
      setMessage(chatInputText);
      // Focus on the input after text is inserted
      inputRef.current?.focus();
    }
  }, [chatInputText]);

  // Update context when local input changes
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setMessage(newValue);
    setChatInputText(newValue);
  };

  // Function to extract visualization IDs from message
  const extractVisualizationIds = (text) => {
    const mentionRegex = /@\s*fig:(\d+)/g;
    const matches = [...text.matchAll(mentionRegex)];
    return matches.map(match => parseInt(match[1]));
  };

  // Function to highlight mentions in the input
  const highlightMentions = (text) => {
    return text.replace(/@\s*fig:(\d+)/g, '<span class="bg-blue-100 text-blue-800 px-1 rounded">@fig:$1</span>');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!message.trim() || !authenticated || !user?.wallet?.address) {
      return;
    }

    const userMessage = message;
    setMessage(''); // Clear input immediately
    setIsLoading(true);

    try {
      // Extract visualization IDs from the message
      const mentionedVisualizationIds = extractVisualizationIds(userMessage);
      console.log('Mentioned visualization IDs:', mentionedVisualizationIds);

      // Add user message immediately
      const userMessageId = Date.now();
      setMessages(prev => [...prev, {
        id: userMessageId,
        text: userMessage,
        isUser: true,
        timestamp: new Date().toISOString()
      }]);

      // Show AI is typing
      const typingId = 'typing-' + Date.now(); // Unique ID for typing indicator
      setMessages(prev => [...prev, {
        id: typingId,
        text: '',
        isUser: false,
        isTyping: true
      }]);

      // Send message and get response
      const response = await sendMessage({
        walletAddress: user.wallet.address,
        canvasId: currentCanvasId,
        text: userMessage,
        mentionedVisualizationIds: mentionedVisualizationIds
      });

      if (!currentCanvasId) {
        setCurrentCanvasId(response.canvas_id);
      }

      // Remove typing indicator and add AI response
      setMessages(prev => {
        // Remove the typing indicator
        const withoutTyping = prev.filter(msg => msg.id !== typingId);
        
        // Add the AI response
        const aiMessage = {
          id: response.ai_message_id,
          text: response.ai_message_text,
          isUser: false,
          timestamp: response.created_at
        };

        // Get the message from the API if needed
        if (response.ai_message_id) {
          getMessage(response.ai_message_id)
            .then(fullMessage => {
              // Update the message with complete data if needed
              setMessages(prev => prev.map(msg => 
                msg.id === response.ai_message_id 
                  ? { ...msg, text: fullMessage.text }
                  : msg
              ));
            })
            .catch(console.error);
        }

        return [...withoutTyping, aiMessage];
      });

      // Handle visualizations if any
      if (response.visualization_ids?.length > 0) {
        console.log('ChatInterface - Processing visualizations:', response.visualization_ids);
        
        // Track if we have any modified visualizations
        let hasModifiedVisualizations = false;
        let firstModifiedOrNewId = null;
        
        setActiveVisualizations(prev => {
          // Create a new array to store the updated visualizations
          const updatedVisualizations = [...prev];
          
          // Process each visualization ID from the response
          response.visualization_ids.forEach(vizId => {
            // Check if this visualization ID already exists in our active list
            const existingIndex = updatedVisualizations.indexOf(vizId);
            
            if (existingIndex >= 0) {
              // This is a modified visualization - it already exists
              console.log(`ChatInterface - Visualization ${vizId} already exists, updating in place`);
              hasModifiedVisualizations = true;
              
              // If we haven't found a modified visualization yet, this is the first one
              if (!firstModifiedOrNewId) {
                firstModifiedOrNewId = vizId;
              }
            } else {
              // This is a new visualization - add it to the list
              console.log(`ChatInterface - Adding new visualization ${vizId}`);
              updatedVisualizations.push(vizId);
              
              // If we haven't found a modified visualization yet, this is the first new one
              if (!firstModifiedOrNewId) {
                firstModifiedOrNewId = vizId;
              }
            }
          });
          
          console.log('ChatInterface - Updated visualization list:', updatedVisualizations);
          return updatedVisualizations;
        });
        
        // Switch to canvas tab
        setActiveTab('canvas');
        
        // If we have a modified or new visualization, we'll need to scroll to it
        // This will be handled by the Canvas component's useEffect
        if (firstModifiedOrNewId) {
          console.log(`ChatInterface - First modified/new visualization ID: ${firstModifiedOrNewId}`);
          // We'll use a custom event to notify the Canvas component
          const event = new CustomEvent('visualizationUpdated', { 
            detail: { visualizationId: firstModifiedOrNewId } 
          });
          window.dispatchEvent(event);
        }
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove typing indicator and show error
      setMessages(prev => {
        const withoutTyping = prev.filter(msg => msg.id !== 'typing');
        return [...withoutTyping, {
          id: Date.now(),
          text: "Failed to get response. Please try again.",
          isUser: false,
          timestamp: new Date().toISOString(),
          isError: true
        }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Update the Message component to handle error messages
  const renderMessages = () => {
    if (isLoadingHistory) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-main"></div>
        </div>
      );
    }

    if (messages.length === 0) {
      return (
        <div className="flex items-center justify-center">
          <h1 className="text-xl text-gray-700 font-normal mt-48">
            {currentCanvasId ? "No messages yet" : "What can I help with?"}
          </h1>
        </div>
      );
    }

    return (
      <div className="w-full">
        {messages.map((msg) => (
          <Message
            key={msg.id}
            text={msg.text}
            isUser={msg.isUser}
            timestamp={msg.timestamp}
            isError={msg.isError}
            isTyping={msg.isTyping}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>
    );
  };

  if (!isChatOpen) {
    return null;
  }

  const isDisabled = !authenticated || isLoading;

  return (
    <div className="flex flex-col h-full w-[400px] min-w-[400px]">
      {/* Fixed MCP Selector Header */}
      <div className="bg-white p-2 flex justify-between items-center sticky top-0 z-10">
        <MCPSelector />
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="w-full">
          {renderMessages()}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t bg-white p-4">
        <div className="w-full">
          <form onSubmit={handleSubmit} className="flex flex-col space-y-2">
            <div className="flex">
              <input
                ref={inputRef}
                type="text"
                value={message}
                onChange={handleInputChange}
                placeholder={authenticated ? "Ask anything... (use @fig:id to reference visualizations)" : "Connect wallet to start chatting..."}
                disabled={isDisabled}
                className="flex-1 px-4 py-3 border rounded-l-lg focus:outline-none focus:ring-1 focus:ring-primary-main focus:border-primary-main text-base disabled:bg-gray-50 disabled:text-gray-500 disabled:border-gray-200"
              />
              <button
                type="submit"
                disabled={isDisabled || !message.trim()}
                className={`px-6 py-3 rounded-r-lg focus:outline-none focus:ring-2 focus:ring-primary-main focus:ring-offset-2 ${
                  isLoading ? 'bg-gray-400' : 'bg-primary-main hover:bg-primary-hover'
                } text-black transition-colors duration-200 whitespace-nowrap`}
              >
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

ChatInterface.propTypes = {
  setActiveTab: PropTypes.func.isRequired,
  setActiveVisualizations: PropTypes.func.isRequired,
};

export default ChatInterface; 