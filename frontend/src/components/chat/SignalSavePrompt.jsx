import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { createSignal } from '../../services/api';
import { useCanvas } from '../../contexts/CanvasContext';
import { usePrivy } from '@privy-io/react-auth';

const SignalSavePrompt = ({ signal, onSaved }) => {
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const { currentCanvasId } = useCanvas();
  const { user } = usePrivy();

  const handleSaveSignal = async () => {
    if (!currentCanvasId || !user?.wallet?.address) return;
    
    setIsSaving(true);
    try {
      // Create a signal object to send to the API
      const signalData = {
        canvas_id: currentCanvasId,
        wallet_address: user.wallet.address,
        signal_definition: signal.signal_definition,
        temp_signal_id: signal.signal_id // Pass the temporary ID for reference if needed
      };
      
      await createSignal(signalData);
      setSaved(true);
      
      // Trigger animation and callback
      if (onSaved) {
        setTimeout(() => {
          onSaved(signal.signal_id);
        }, 500); // Short delay for animation to be visible
      }
      
    } catch (error) {
      console.error('Error saving signal:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (saved) {
    return (
      <div className="flex items-center space-x-2 p-2 mt-1 bg-green-50 text-green-800 rounded-md text-sm">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
        <span>Signal saved successfully</span>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between p-2 mt-1 bg-blue-50 text-blue-800 rounded-md text-sm">
      <div className="flex items-center space-x-2">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>Trading signal detected. Would you like to save it?</span>
      </div>
      <button
        onClick={handleSaveSignal}
        disabled={isSaving}
        className={`px-3 py-1 rounded ${
          isSaving 
            ? 'bg-gray-300 text-gray-700' 
            : 'bg-primary-main text-black hover:bg-primary-hover'
        } transition-colors duration-200`}
      >
        {isSaving ? (
          <div className="flex items-center space-x-1">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-black"></div>
            <span>Saving</span>
          </div>
        ) : (
          'Save Signal'
        )}
      </button>
    </div>
  );
};

SignalSavePrompt.propTypes = {
  signal: PropTypes.shape({
    signal_id: PropTypes.string.isRequired,
    signal_definition: PropTypes.string.isRequired
  }).isRequired,
  onSaved: PropTypes.func
};

export default SignalSavePrompt; 