import React, { useState } from 'react';
import { useChatContext } from '../../contexts/ChatContext';
import { usePrivy } from '@privy-io/react-auth';

const Signals = () => {
  const { authenticated } = usePrivy();
  const { setChatInputText } = useChatContext();
  
  // Dummy data for signals
  const [signals] = useState([
    { id: 1, name: "ETHUSD Bearish Divergence", createdAt: "2023-12-01", description: "RSI divergence on 4h timeframe" },
    { id: 2, name: "BTC Golden Cross", createdAt: "2023-12-05", description: "50 & 200 MA cross on daily chart" },
    { id: 3, name: "AVAX Volume Spike", createdAt: "2023-12-10", description: "Unusual volume pattern detected" },
    { id: 4, name: "SOL Bullish Pattern", createdAt: "2023-12-15", description: "Inverse head and shoulders formation" },
    { id: 5, name: "ARB Support Bounce", createdAt: "2023-12-20", description: "Price bounced off major support level" }
  ]);
  
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
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {signals.map((signal) => (
              <tr key={signal.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {signal.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {signal.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {signal.createdAt}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {signal.description}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => addSignalToChat(signal.id)}
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