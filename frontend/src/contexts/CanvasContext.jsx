import React, { createContext, useContext, useState } from 'react';

const CanvasContext = createContext();

export function CanvasProvider({ children }) {
  const [currentCanvasId, setCurrentCanvasId] = useState(null);

  const clearCanvas = () => {
    setCurrentCanvasId(null);
  };

  return (
    <CanvasContext.Provider value={{ currentCanvasId, setCurrentCanvasId, clearCanvas }}>
      {children}
    </CanvasContext.Provider>
  );
}

export function useCanvas() {
  return useContext(CanvasContext);
} 