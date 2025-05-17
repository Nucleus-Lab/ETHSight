import React, { useState } from 'react';
import { subscribe } from '../../utils/contracts';
import { usePrivy, useWallets } from '@privy-io/react-auth';
import { showTransactionNotification } from '../../utils/notifications';

const SubscribeButton = () => {
  const { user, authenticated } = usePrivy();
  const [isLoading, setIsLoading] = useState(false);
  const { wallets } = useWallets();

  const handleSubscribe = async () => {
    if (!authenticated || !user?.wallet?.address) {
      return;
    }
    
    try {
      setIsLoading(true);
      console.log('Initiating subscription process');
      
      // Subscribe using the wallet
      const result = await subscribe(wallets[0]);
      console.log('Subscription transaction:', result.hash);
      
      // Show the transaction notification
      showTransactionNotification(result.hash);
      
      // Give the blockchain some time to update
      setTimeout(() => {
        setIsLoading(false);
        // You might want to add a success notification here
      }, 2000);
    } catch (err) {
      console.error('Error subscribing:', err);
      setIsLoading(false);
    }
  };

  if (!authenticated) {
    return null;
  }

  return (
    <button
      onClick={handleSubscribe}
      className="min-w-[160px] px-6 py-3 bg-primary-main text-black rounded-lg hover:bg-primary-hover transition-colors duration-200 font-medium disabled:bg-gray-300"
      disabled={isLoading}
    >
      {isLoading ? 'Processing...' : 'Subscribe Now'}
    </button>
  );
};

export default SubscribeButton; 