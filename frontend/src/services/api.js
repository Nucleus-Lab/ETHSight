// get the base url from the environment variable
const BACKEND_API_BASE_URL = import.meta.env.VITE_BACKEND_API_BASE_URL;

export const createUser = async (walletAddress) => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/users/${walletAddress}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    }); 

    if (!response.ok) {
      throw new Error('Failed to create user');
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating user:', error);
    throw error;
  }
};

export const sendMessage = async ({ walletAddress, canvasId = null, text, mentionedVisualizationIds = [] }) => {
  try {
    console.log('Sending request with:', { walletAddress, canvasId, text, mentionedVisualizationIds }); // Debug log
    const response = await fetch(`${BACKEND_API_BASE_URL}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        wallet_address: walletAddress,
        canvas_id: canvasId,
        text: text,
        mentioned_visualization_ids: mentionedVisualizationIds
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send message');
    }

    const data = await response.json();
    console.log('Response data structure:', {
      keys: Object.keys(data),
      hasSignals: !!data.signals,
      signalsType: data.signals ? typeof data.signals : 'not present',
      signalsValue: data.signals
    }); // Debug log for response structure
    return data;
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

export const getUserCanvases = async (walletAddress) => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/canvas/user/${walletAddress}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch canvases');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching canvases:', error);
    throw error;
  }
};

export const getCanvasFirstMessage = async (canvasId) => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/canvas/${canvasId}/first-message`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch first message');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching first message:', error);
    throw error;
  }
};

export const getCanvasFirstVisualization = async (canvasId) => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/canvas/${canvasId}/first-visualization`);

    console.log('Response from getCanvasFirstVisualization:', response);
    
    if (!response.ok) {
      throw new Error('Failed to fetch first visualization');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching first visualization:', error);
    throw error;
  }
};

export const getCanvasMessages = async (canvasId) => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/canvas/${canvasId}/messages`);
    
    console.log('Response from getCanvasMessages:', response);

    if (!response.ok) {
      throw new Error('Failed to fetch messages');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching messages:', error);
    throw error;
  }
};

export const getVisualization = async (visualizationId) => {
  console.log(`API - Starting fetch for visualization ${visualizationId}`);
  
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/visualization/${visualizationId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log(`API - Response status for visualization ${visualizationId}:`, response.status);

    // Log the raw response text first
    const responseText = await response.text();
    console.log(`API - Raw response for visualization ${visualizationId}:`, responseText);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}, body: ${responseText}`);
    }

    // Try to parse the text as JSON
    let data;
    try {
      data = JSON.parse(responseText);
      console.log(`API - Parsed visualization ${visualizationId} data:`, data);
    } catch (parseError) {
      console.error(`API - JSON parsing error for visualization ${visualizationId}:`, {
        error: parseError,
        receivedText: responseText.substring(0, 200) + '...' // Show first 200 chars
      });
      throw parseError;
    }

    return {
      id: visualizationId,
      data: data
    };
  } catch (error) {
    console.error(`API - Error fetching visualization ${visualizationId}:`, {
      error: error,
      message: error.message,
      stack: error.stack
    });
    throw error;
  }
};

export const getMessage = async (messageId) => {
  try {
    console.log(`Fetching message with ID: ${messageId}`);
    const response = await fetch(`${BACKEND_API_BASE_URL}/message/${messageId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log('Response from getMessage:', response);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch message');
    }

    const data = await response.json();
    console.log('Message data:', data);
    return data;
  } catch (error) {
    console.error('Error fetching message:', error);
    throw error;
  }
};

export const getMCPServers = async () => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/mcp/servers`);
    if (!response.ok) {
      throw new Error('Failed to fetch MCP servers');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching MCP servers:', error);
    throw error;
  }
};

export const getCurrentMCP = async () => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/mcp/current`);
    if (!response.ok) {
      throw new Error('Failed to fetch current MCP server');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching current MCP server:', error);
    throw error;
  }
};

export const selectMCPServer = async (serverName) => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/mcp/select/${serverName}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to select MCP server');
    }
    return await response.json();
  } catch (error) {
    console.error('Error selecting MCP server:', error);
    throw error;
  }
};

export const getCanvasVisualizations = async (canvasId) => {
  try {
    const response = await fetch(`${BACKEND_API_BASE_URL}/canvas/${canvasId}/visualizations`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch canvas visualizations');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching canvas visualizations:', error);
    throw error;
  }
};

// Get all signals for a specific canvas
export const getSignalsForCanvas = async (canvasId) => {
  try {
    console.log(`Fetching signals for canvas: ${canvasId}`);
    const response = await fetch(`${BACKEND_API_BASE_URL}/canvas/${canvasId}/signals`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch signals for canvas');
    }
    
    const data = await response.json();
    console.log('Canvas signals data:', data);
    return data;
  } catch (error) {
    console.error('Error fetching signals for canvas:', error);
    throw error;
  }
};

// Get all signals for a user by wallet address
export const getAllSignalsForUser = async (walletAddress) => {
  try {
    console.log(`Fetching signals for user: ${walletAddress}`);
    const response = await fetch(`${BACKEND_API_BASE_URL}/signals/user/${walletAddress}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch signals for user');
    }
    
    const data = await response.json();
    console.log('User signals data:', data);
    return data;
  } catch (error) {
    console.error('Error fetching signals for user:', error);
    throw error;
  }
};

// Create a new signal
export const createSignal = async (signalData) => {
  try {
    console.log('Creating signal with data:', signalData);
    const response = await fetch(`${BACKEND_API_BASE_URL}/signal`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(signalData)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create signal');
    }
    
    const data = await response.json();
    console.log('Created signal:', data);
    return data;
  } catch (error) {
    console.error('Error creating signal:', error);
    throw error;
  }
};