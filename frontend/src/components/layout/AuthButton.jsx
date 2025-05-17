import React, { useEffect, useState, useRef } from 'react';
import { usePrivy, useLogout } from '@privy-io/react-auth';
import { createUser } from '../../services/api';
import { useCanvas } from '../../contexts/CanvasContext';
import SubscriptionCheck from './SubscriptionCheck';

const AuthButton = () => {
  const { login, ready, authenticated, user } = usePrivy();
  const { clearCanvas } = useCanvas();
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const dropdownRef = useRef(null);
  

  const { logout } = useLogout({
    onSuccess: () => {
      console.log('Successfully logged out');
      clearCanvas(); // Clear canvas context on logout
      setShowDropdown(false);
      // Clear any local state if needed
      localStorage.removeItem('username');
      localStorage.removeItem('walletAddress');
    }
  });

  // Handle clicks outside of dropdown to close it
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Handle user authentication
  useEffect(() => {
    const handleUserAuth = async () => {
      if (authenticated && user?.wallet?.address && !isCreatingUser) {
        try {
          setIsCreatingUser(true);
          const userData = await createUser(user.wallet.address);
          console.log('User created/retrieved:', userData);
        } catch (error) {
          console.error('Failed to create/get user:', error);
        } finally {
          setIsCreatingUser(false);
        }
      }
    };

    handleUserAuth();
  }, [authenticated, user?.wallet?.address]);

  // Show loading state while Privy is initializing
  if (!ready) {
    return (
      <button 
        className="px-4 py-2 bg-gray-100 text-gray-400 rounded-lg animate-pulse"
        disabled
      >
        Loading...
      </button>
    );
  }

  // If creating user, show loading state
  if (isCreatingUser) {
    return (
      <button 
        className="px-4 py-2 bg-gray-100 text-gray-400 rounded-lg animate-pulse"
        disabled
      >
        Setting up...
      </button>
    );
  }

  // If authenticated, show wallet address with subscription check
  if (authenticated && user?.wallet?.address) {
    const shortAddress = `${user.wallet.address.slice(0, 6)}...${user.wallet.address.slice(-4)}`;
    
    return (
      <>
        <SubscriptionCheck 
          walletAddress={user.wallet.address}
          onSubscriptionStatus={setIsSubscribed}
        />
        <div className="relative" ref={dropdownRef}>
          {/* Wallet Address Button */}
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="px-4 py-2 bg-gray-100 rounded-lg text-gray-700 font-medium hover:bg-gray-200 transition-colors duration-200"
          >
            {shortAddress}
          </button>

          {/* Dropdown Menu */}
          {showDropdown && (
            <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
              <div className="py-1">
                <button
                  onClick={async () => {
                    try {
                      await logout();
                    } catch (error) {
                      console.error('Error logging out:', error);
                    }
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                >
                  Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </>
    );
  }

  

  // If not authenticated, show connect button
  return (
    <button
      onClick={() => login()}
      className="px-4 py-2 bg-primary-main hover:bg-primary-hover text-black rounded-lg transition-colors duration-200 font-medium"
    >
      Connect Wallet
    </button>
  );
};

export default AuthButton; 