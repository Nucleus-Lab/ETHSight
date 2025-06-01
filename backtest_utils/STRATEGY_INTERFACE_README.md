# Strategy Interface README

## Overview

The Strategy Interface module provides a simplified, clean API for integrating backtesting functionality with your strategy.py. It abstracts away the complexity of the original backtesting system and provides two main functions with simple inputs and outputs.

## 🔧 Recent Updates

- **Fixed GeckoTerminal API Endpoint**: Updated `search_pools` method to use the correct `/search/pools` endpoint according to the official GeckoTerminal API documentation
- **Enhanced Search Functionality**: Added support for optional network filtering and improved error handling
- **Better Pool Discovery**: Improved pool address discovery with fallback to cross-network search

## Features

- **Simplified AI Indicator Generation**: Generate trading indicators from natural language descriptions
- **Automated Data Fetching**: Automatically fetch OHLC data from GeckoTerminal API
- **Comprehensive Backtesting**: Run complete backtests with trading statistics and visualizations
- **Clean API**: Simple function interfaces that are easy to integrate

## Functions

### 1. `generate_indicator_from_prompt()`

Generate AI-powered trading indicators from natural language descriptions.

**Inputs:**
- `user_prompt` (str): Natural language description of the indicator
- `indicator_name` (str): Name for the indicator
- `api_key` (str, optional): OpenAI API key (uses environment variable if not provided)
- `model` (str): OpenAI model to use (default: 'gpt-4o')

**Returns:**
- `tuple`: (indicator_file_path, indicator_name)

**Example:**
```python
from backtest_utils.strategy_interface import generate_indicator_from_prompt

file_path, name = generate_indicator_from_prompt(
    user_prompt="Create a RSI indicator with overbought at 70 and oversold at 30",
    indicator_name="RSI_Strategy"
)
```

### 2. `run_backtest_with_indicators()`

Run a complete backtest with generated indicators.

**Inputs:**
- `network` (str): Network ID (e.g., 'eth', 'bsc')
- `token_symbol` (str): Token symbol (e.g., 'ETH', 'BTC')
- `timeframe` (str): Timeframe (e.g., '1m', '15m', '1h', '1d')
- `time_start` (str): Start time in ISO format
- `time_end` (str): End time in ISO format
- `buy_indicator_name` (str): Name of buy indicator
- `sell_indicator_name` (str, optional): Name of sell indicator

**Returns:**
- `dict`: Dictionary containing:
  - `trading_stats`: Trading performance statistics
  - `plotly_figure`: Plotly figure JSON for visualization
  - `buy_indicator_info`: Information about the buy indicator
  - `sell_indicator_info`: Information about the sell indicator
  - `data_points`: Number of data points used
  - `time_range`: Actual time range of the data

**Example:**
```python
from backtest_utils.strategy_interface import run_backtest_with_indicators

result = run_backtest_with_indicators(
    network="eth",
    token_symbol="ETH",
    timeframe="1d",
    time_start="2024-01-01T00:00:00Z",
    time_end="2024-02-01T00:00:00Z",
    buy_indicator_name="RSI_Buy",
    sell_indicator_name="RSI_Sell"
)

# Access trading stats
stats = result['trading_stats']
print(f"Total trades: {stats['total_trades']}")
print(f"Win rate: {stats['win_rate']:.2f}%")
print(f"Total return: {stats['total_return']:.2f}%")

# Access plotly figure
plotly_json = result['plotly_figure']
```

## Integration with strategy.py

Here's how to integrate these functions into your FastAPI strategy.py:

```python
from backtest_utils.strategy_interface import (
    generate_indicator_from_prompt,
    run_backtest_with_indicators
)

@router.post("/strategy/backtest")
async def run_backtest(strategy: StrategyModel, db: Session = Depends(get_db)):
    try:
        # Get signal information from database
        buy_signal = get_signal_info(db, strategy.buyCondition.signal_id)
        sell_signal = get_signal_info(db, strategy.sellCondition.signal_id)
        
        # Generate indicators
        buy_indicator_name = buy_signal.signal_name.replace(" ", "_")
        buy_file_path, buy_name = generate_indicator_from_prompt(
            user_prompt=buy_signal.signal_description,
            indicator_name=buy_indicator_name
        )
        
        sell_indicator_name = sell_signal.signal_name.replace(" ", "_")
        sell_file_path, sell_name = generate_indicator_from_prompt(
            user_prompt=sell_signal.signal_description,
            indicator_name=sell_indicator_name
        )
        
        # Run backtest
        backtest_result = run_backtest_with_indicators(
            network="eth",  # Can be made configurable
            token_symbol="ETH",  # Get from filter signal
            timeframe="1d",  # Can be made configurable
            time_start=strategy.timeRange['start'],
            time_end=strategy.timeRange['end'],
            buy_indicator_name=buy_name,
            sell_indicator_name=sell_name
        )
        
        return {
            "status": "success",
            "backtest_results": backtest_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Data Flow

1. **Indicator Generation**: User provides natural language description → AI generates Python indicator code → Code is saved to file
2. **Data Fetching**: Token symbol → Search GeckoTerminal for pool → Fetch OHLC data → Save to CSV
3. **Backtesting**: Load indicators → Apply to data → Calculate trading signals → Compute statistics → Generate visualization

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for AI indicator generation
- Other environment variables are handled by the existing backtesting system

### Directory Structure

The interface creates and uses the following directories:
- `indicators/`: Stores generated indicator Python files
- `data/`: Stores fetched OHLC data (CSV files)
- `json_charts/`: Stores Plotly figure JSON files

## Error Handling

Both functions include comprehensive error handling:
- Network connection issues
- API rate limits
- Invalid input parameters
- Missing dependencies
- File system errors

Errors are logged with detailed messages and stack traces for debugging.

## Testing

Use the provided test script to verify functionality:

```bash
cd backtest_utils
python test_strategy_interface.py
```

This will:
1. Generate sample indicators
2. Run a backtest with real data
3. Display results and statistics

## Supported Networks and Tokens

The interface supports any network and token available on GeckoTerminal:
- **Networks**: eth, bsc, polygon, arbitrum, optimism, etc.
- **Tokens**: Any token with available liquidity pools

## Timeframes

Supported timeframes:
- `1m`, `5m`, `15m`: Minute-level data
- `1h`, `4h`: Hourly data  
- `1d`: Daily data

## Trading Statistics

The backtest results include:
- `total_trades`: Number of completed buy-sell cycles
- `profitable_trades`: Number of profitable trades
- `win_rate`: Percentage of profitable trades
- `total_return`: Total portfolio return percentage
- `avg_return`: Average return per trade
- `trades`: Detailed list of individual trades

## Visualization

The Plotly figure includes:
- Price chart with OHLC data
- Indicator overlays
- Buy/sell signal markers
- Interactive features for detailed analysis

## Performance Considerations

- Large datasets are automatically resampled for better performance
- Data is cached locally to avoid redundant API calls
- Batch processing for database operations
- Memory-efficient data handling

## Dependencies

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

Key dependencies:
- `pandas`: Data manipulation
- `numpy`: Numerical computations
- `plotly`: Interactive visualizations
- `requests`: API communication
- `openai`: AI indicator generation
- `matplotlib`: Static plots (fallback)

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Review the test script for usage examples 