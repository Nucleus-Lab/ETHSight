# SignalFlow: Data-Driven On-Chain Insights and Trading Platform

In the rapidly evolving crypto market, identifying alpha, validating strategies, and executing trades in real time is critical. ⚡ SignalFlow is an all-in-one platform designed to streamline this process through a data-driven trading loop.

## Core Modules

1. Signal Discovery

- Query any on-chain data using natural language (e.g. large transfers, DEX activity, active wallets).
- Visualize results instantly with interactive charts.
- Save and reuse signals in downstream strategies.

2. Strategy Backtesting

- Backtest any signal combination with historical data.
- Evaluate performance via key metrics like PnL, drawdown, and Sharpe ratio.
- Quantify edge and validate ideas before deployment.

3. Real-Time Execution

- Combine signals, define trigger conditions, and monitor live on-chain activity.
- Automatically execute buy/sell actions when criteria are met.
- Close the loop from insight to trade with full automation.

## Architecture

### 1. AI Agents
- Intelligent agents for processing and responding to user queries
- Natural language understanding and generation
- Integration with the chat interface
- MCP (Message Control Protocol) for managing agent responses

### 2. Backend
- Python-based server (>= 3.10)
- Handles communication between frontend and AI agents
- API endpoints for subscription and visualization data

### 3. Frontend
- React-based web application
- Features:
  - Chat interface with AI agents
  - Subscription management
  - Visualization canvas
  - File management system
- Change theme color in src/constants/colors.js and tailwind.config.js

### 4. Smart Contracts (Hardhat)
- Subscription NFT system
- Deployed on network:
  - BSC Testnet: [https://testnet.bscscan.com/address/0x77EE0B4f2e96A369dC82B20834b50032921D8801](https://testnet.bscscan.com/address/0x77EE0B4f2e96A369dC82B20834b50032921D8801)

## Getting Started

### Prerequisites
- Node.js >= 16
- Python >= 3.10
- Hardhat
- MetaMask or compatible Web3 wallet

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd <project-directory>
```

2. Install AI Agents dependencies
```bash
cd agents
pip install -r requirements.txt
```

3. Install Backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

4. Install Frontend dependencies
```bash
cd frontend
npm install
```

5. Install and compile contracts
```bash
cd hardhat
npm install
npx hardhat compile
```

### Configuration

1. Set up environment variables
```bash
# Create .env files in each component directory
cp .env.example .env
```

2. Configure the following in your .env files:
- AI API keys
- Backend server URLs
- Contract addresses
- Network configurations

### Running the Project

1. Start the Backend server
```bash
uvicorn backend.main:app --reload
```

3. Start the Frontend development server
```bash
cd frontend
npm run dev
```

4. Deploy contracts (if needed)
```bash
cd hardhat
npx hardhat run scripts/deploy.js --network <network-name>
```

## Development

### Project Structure
```
├── agents/ # AI agents implementation
├── backend/ # Python backend server
├── frontend/ # React frontend application
└── hardhat/ # Smart contract development
```