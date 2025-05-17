import React, { useEffect, useState, useRef } from 'react';
import { checkSubscription, subscribe } from '../../utils/contracts';
import { usePrivy, useWallets } from '@privy-io/react-auth';
import { showTransactionNotification } from '../../utils/notifications';

const formatExpiryDate = (timestamp) => {
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diffTime = date - now;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  const dateStr = date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  return {
    fullDate: dateStr,
    daysRemaining: diffDays
  };
};

const SubscriptionCheck = ({ onSubscriptionStatus }) => {
  const { user, authenticated } = usePrivy();
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expiryDate, setExpiryDate] = useState(null);
  const { wallets, ready: walletsReady } = useWallets();

  useEffect(() => {
    const checkSubscriptionStatus = async () => {
      if (!authenticated || !user || !user.wallet) {
        setIsLoading(false);
        setIsSubscribed(false);
        onSubscriptionStatus(false);
        return;
      }
      
      try {
        setIsLoading(true);
        setError(null);
        setExpiryDate(null);

        console.log('Checking subscription for user:', user.id);
        
        // Now check subscription using the signer's address
        const { hasSubscription, expiryDate: expiry } = await checkSubscription(user.wallet.address, wallets[0]);
        console.log('Subscription status:', { hasSubscription, expiryDate: expiry });
        
        setIsSubscribed(hasSubscription);
        if (expiry) {
          setExpiryDate(expiry.getTime() / 1000); // Convert to Unix timestamp
        }
        onSubscriptionStatus(hasSubscription);
      } catch (err) {
        console.error('Error checking subscription:', err);
        setError(err.message || 'Error checking subscription');
        setIsSubscribed(false);
        onSubscriptionStatus(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkSubscriptionStatus();
  }, [authenticated, user, onSubscriptionStatus]);

  const handleSubscribe = async () => {
    if (!authenticated || !user || !user.wallet) {
      setError('Please connect your wallet first');
      return;
    }
    
    try {
      setIsLoading(true);
      setError(null);

      console.log('Initiating subscription process for user:', user.id);
      
      // Now subscribe using the wallet
      const result = await subscribe(wallets[0]);
      console.log('Subscription transaction:', result.hash);
      
      // Show the transaction notification
      showTransactionNotification(result.hash);
      
      // Wait for a moment to allow the blockchain to update
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Recheck subscription status
      const { hasSubscription, expiryDate: expiry } = await checkSubscription(user.wallet.address, wallets[0]);
      setIsSubscribed(hasSubscription);
      if (expiry) {
        setExpiryDate(expiry.getTime() / 1000);
      }
      onSubscriptionStatus(hasSubscription);
    } catch (err) {
      console.error('Error subscribing:', err);
      setError(err.message || 'Error subscribing');
    } finally {
      setIsLoading(false);
    }
  };

  if (!authenticated) {
    return (
      <div className="flex flex-col items-center">
        <p className="text-sm text-gray-500 mb-2">Please connect your wallet to subscribe</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <button 
        className="px-4 py-2 bg-gray-100 text-gray-400 rounded-lg animate-pulse min-w-[250px]"
        disabled
      >
        Checking subscription...
      </button>
    );
  }

  if (!isSubscribed) {
    return (
      <div className="flex items-center space-x-2">
        <button
          onClick={handleSubscribe}
          className={`min-w-[160px] px-6 py-2 bg-primary-main text-black rounded-lg hover:bg-primary-hover transition-colors duration-200 font-medium disabled:bg-gray-300`}
          disabled={isLoading}
        >
          {isLoading ? 'Processing...' : 'Subscribe Now'}
        </button>
        {error && (
          <div 
            className="text-red-500 cursor-help"
            title={error}
          >
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              className="h-5 w-5" 
              viewBox="0 0 20 20" 
              fill="currentColor"
            >
              <path 
                fillRule="evenodd" 
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" 
                clipRule="evenodd" 
              />
            </svg>
          </div>
        )}
      </div>
    );
  }

  if (isSubscribed && expiryDate) {
    const { fullDate, daysRemaining } = formatExpiryDate(expiryDate);
    
    return (
      <div className="flex items-center space-x-2">
        <div className="px-3 py-1 text-green-800 rounded-lg text-sm">
          <div className="flex items-center min-w-[180px]">
            <svg className="w-4 h-4 mr-1.5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>
              Subscribed
              <span className="mx-1">•</span>
              <span className="font-medium" title={`Expires: ${fullDate}`}>
                {daysRemaining > 0 
                  ? `${daysRemaining} days left`
                  : 'Expires today'}
              </span>
            </span>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default SubscriptionCheck; 