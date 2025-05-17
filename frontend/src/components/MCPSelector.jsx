import React, { useState, useEffect, useRef } from 'react';
import { getMCPServers, getCurrentMCP, selectMCPServer } from '../services/api';

const MCPSelector = () => {
  const [mcpServers, setMcpServers] = useState([]);
  const [currentServer, setCurrentServer] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isChanging, setIsChanging] = useState(false);
  const [currentDescription, setCurrentDescription] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    loadMCPData();

    // Close dropdown when clicking outside
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const loadMCPData = async () => {
    try {
      const [servers, current] = await Promise.all([
        getMCPServers(),
        getCurrentMCP()
      ]);
      setMcpServers(servers);
      setCurrentServer(current.current_server);
      
      // Find current server description
      const currentServerObj = servers.find(server => server.name === current.current_server);
      if (currentServerObj) {
        setCurrentDescription(currentServerObj.description);
      }
    } catch (error) {
      console.error('Error loading MCP data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleServerChange = async (newServer) => {
    if (newServer === currentServer) {
      setIsOpen(false);
      return;
    }
    
    setIsChanging(true);
    try {
      await selectMCPServer(newServer);
      setCurrentServer(newServer);
      
      // Update description
      const selectedServer = mcpServers.find(server => server.name === newServer);
      if (selectedServer) {
        setCurrentDescription(selectedServer.description);
      }
      
      // Show a success message
      const message = document.createElement('div');
      message.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg transition-opacity duration-500';
      message.textContent = `Switched to ${selectedServer?.description || newServer} data source`;
      document.body.appendChild(message);
      
      // Remove the message after 3 seconds
      setTimeout(() => {
        message.style.opacity = '0';
        setTimeout(() => document.body.removeChild(message), 500);
      }, 3000);

    } catch (error) {
      console.error('Error changing MCP server:', error);
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg transition-opacity duration-500';
      errorMessage.textContent = 'Failed to switch data source';
      document.body.appendChild(errorMessage);
      
      setTimeout(() => {
        errorMessage.style.opacity = '0';
        setTimeout(() => document.body.removeChild(errorMessage), 500);
      }, 3000);
    } finally {
      setIsChanging(false);
      setIsOpen(false);
    }
  };

  if (isLoading) {
    return (
      <div className="h-8 w-8 flex items-center justify-center animate-pulse">
        <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
      </div>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Icon button */}
      <div 
        className="h-8 w-8 flex items-center justify-center cursor-pointer rounded-full hover:bg-gray-100 transition-colors duration-200 group relative"
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => setIsOpen(true)}
        title={currentDescription}
      >
        <svg 
          className="h-5 w-5 text-gray-600" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
        
        {/* Current server indicator dot */}
        <div className="absolute bottom-0 right-0 h-2 w-2 bg-primary-main rounded-full"></div>
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div 
          className="absolute left-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[200px] z-10"
          onMouseLeave={() => setIsOpen(false)}
        >
          <div className="px-3 py-1 text-xs text-gray-500 font-medium border-b border-gray-100">
            Select Data Source
          </div>
        {mcpServers.map((server) => (
            <div 
              key={server.name} 
              className={`px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 flex items-center justify-between ${server.name === currentServer ? 'text-primary-main font-medium' : 'text-gray-700'}`}
              onClick={() => handleServerChange(server.name)}
            >
            {server.description}
              {server.name === currentServer && (
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </div>
        ))}
        </div>
      )}
      
      {/* Loading spinner */}
      {isChanging && (
        <div className="absolute -right-6 top-1/2 transform -translate-y-1/2 w-4 h-4 border-2 border-primary-main border-t-transparent rounded-full animate-spin"></div>
      )}
    </div>
  );
};

export default MCPSelector; 