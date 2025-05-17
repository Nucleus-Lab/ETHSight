import React, { useState, useEffect } from 'react';
import { useChatContext } from '../../contexts/ChatContext';
import { usePrivy } from '@privy-io/react-auth';
import { getAllSignalsForUser } from '../../services/api';

const Signals = () => {
  const { authenticated, user } = usePrivy();
  const { setChatInputText } = useChatContext();
  
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Fetch signals when component mounts
  useEffect(() => {
    const fetchSignals = async () => {
      if (!authenticated || !user?.wallet?.address) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const userSignals = await getAllSignalsForUser(user.wallet.address);
        console.log('Fetched user signals:', userSignals);
        setSignals(userSignals);
      } catch (err) {
        console.error('Error fetching signals:', err);
        setError('Failed to load signals. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchSignals();
  }, [authenticated, user?.wallet?.address]);
  
  const addSignalToChat = (signalId) => {
    // Use the Context function to append to chat input
    setChatInputText((currentText) => {
      // If there's already text, add a space before appending
      const prefix = currentText && !currentText.endsWith(' ') ? ' ' : '';
      return `${currentText}${prefix}@signal:${signalId}`;
    });
  };
  
  // Show authentication message if user is not authenticated
  if (!authenticated) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-gray-500">Please connect your wallet to view your saved signals</p>
      </div>
    );
  }
  
  // Show loading state
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-main"></div>
      </div>
    );
  }
  
  // Show error state
  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }
  
  // Show empty state
  if (signals.length === 0) {
    return (
      <div className="h-full flex items-center justify-center flex-col">
        <p className="text-gray-500 mb-2">No signals found</p>
        <p className="text-sm text-gray-400">Start creating signals in your chat conversations</p>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto py-4">
      <h2 className="text-xl font-semibold mb-4">Saved Signals</h2>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {signals.map((signal) => (
              <tr key={signal.signal_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {signal.signal_id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {signal.signal_name}
                </td>
                <td className="px-6 py-4 whitespace-pre-wrap text-sm text-gray-500 max-w-md">
                  {signal.signal_description}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(signal.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => addSignalToChat(signal.signal_id)}
                    className="px-3 py-1 bg-primary-main text-black rounded hover:bg-primary-hover transition-colors duration-200"
                  >
                    Use for backtest
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Signals; 