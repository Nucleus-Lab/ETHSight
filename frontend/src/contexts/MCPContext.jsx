import React, { createContext, useContext, useState, useEffect } from 'react';
import { getMCPServers, getCurrentMCP } from '../services/api';

const MCPContext = createContext();

export const MCPProvider = ({ children }) => {
  const [mcpServers, setMcpServers] = useState([]);
  const [currentServer, setCurrentServer] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const loadMCPData = async () => {
    try {
      const [servers, current] = await Promise.all([
        getMCPServers(),
        getCurrentMCP()
      ]);
      setMcpServers(servers);
      setCurrentServer(current.current_server);
    } catch (error) {
      console.error('Error loading MCP data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMCPData();
  }, []);

  const value = {
    mcpServers,
    currentServer,
    setCurrentServer,
    isLoading,
    loadMCPData
  };

  return (
    <MCPContext.Provider value={value}>
      {children}
    </MCPContext.Provider>
  );
};

export const useMCP = () => {
  const context = useContext(MCPContext);
  if (!context) {
    throw new Error('useMCP must be used within an MCPProvider');
  }
  return context;
}; 