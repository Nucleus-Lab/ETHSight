import os
import requests
import sys
import logging
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 从环境变量获取 API 密钥
API_KEY = os.getenv("ONEINCH_API_KEY")
if not API_KEY:
    logger.error("ONEINCH_API_KEY 环境变量未设置")
    # 为测试目的，我们将继续使用虚拟密钥而不是抛出错误
    API_KEY = "dummy_key_for_testing"
    logger.warning("使用测试用的虚拟 API 密钥")

# 1inch API 基础 URL
BASE_URL = "https://api.1inch.dev/history/v2.0"
PORTFOLIO_BASE_URL = "https://api.1inch.dev/portfolio/portfolio/v4"

# 创建 MCP 服务器
mcp = FastMCP("1inch History API")

#############################
# TOOLS
#############################
@mcp.tool()
def get_ohlcv_data(
    pool_address: str,
    network: str = "eth",
    timeframe: str = "day",
    aggregate: int = 1,
    before_timestamp: int = 1747367067,
    limit: int = 100,
    currency: str = "usd",
    token: str = "base",
    include_empty_intervals: bool = True
):
    """
    Fetch OHLCV data from GeckoTerminal for a given pool.

    Args:
        pool_address (str): The pool address (e.g., Uniswap v3 pool).
        network (str): Blockchain network (e.g., "eth", "bsc").
        timeframe (str): Time scale of the OHLCV data (e.g., "day", "hour", "minute")
        aggregate (int): Time aggregation interval (how many timeframes).
        before_timestamp (int): UNIX timestamp to fetch data before.
        limit (int): Number of data points to fetch.
        currency (str): "usd" or another quote currency.
        token (str): "base" or "quote" token.
        include_empty_intervals (bool): Whether to include empty time intervals.

    Returns:
        dict: Parsed JSON response from GeckoTerminal.
    """
    url = f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
    params = {
        "aggregate": aggregate,
        "before_timestamp": before_timestamp,
        "limit": limit,
        "currency": currency,
        "token": token,
        "include_empty_intervals": str(include_empty_intervals).lower(),
    }
    headers = {
        "accept": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# if __name__ == '__main__':
#     print(get_ohlcv_data(
#         pool_address='0x60594a405d53811d3bc4766596efd80fd545a270',  # DAI
#         network="eth",
#         timeframe="day",
#         aggregate = 1,
#         before_timestamp=1747367067,
#         limit=100,
#         currency="usd",
#         token="base",
#         include_empty_intervals=True
#     ))

# Run the server
if __name__ == "__main__":
    # Record server startup
    logger.info("Starting OHLCV MCP server, using stdio transport")
    logger.info(f"Python version: {sys.version}")
    logger.info("Server initialized and ready")
    
    try:
        # Use stdio transport, which is supported by FastMCP
        # This will allow the server to communicate via standard input/output
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Running MCP server failed: {str(e)}")
        raise