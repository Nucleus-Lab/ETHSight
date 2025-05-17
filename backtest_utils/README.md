# GeckoTerminal 链上数据回溯系统

这是一个基于 Python 的链上数据回溯系统，专注于从 GeckoTerminal DEX API 获取和分析 OHLC 数据。系统支持多种时间周期的数据获取、存储和分析，可用于 DEX 交易池的历史数据回溯和技术分析。

## 功能特点

- 从 GeckoTerminal API 获取 DEX 交易池的 OHLC 数据
- 支持多种时间周期（日、小时、分钟）和聚合周期
- 灵活的数据存储选项（CSV 和 SQLite）
- 丰富的技术分析指标计算
- **AI 驱动的指标生成**：使用自然语言描述创建自定义指标
- 交易信号可视化和策略性能评估
- 数据可视化和交互式图表生成
- 命令行界面，易于使用和自动化

## 项目结构

```
geckoterminal_backtracker/
│   ├─ api/                  # API 交互模块
│   │   ├─ __init__.py
│   │   └─ gecko_api.py      # GeckoTerminal API 客户端
│   ├─ storage/              # 数据存储模块
│   │   ├─ __init__.py
│   │   ├─ csv_storage.py    # CSV 存储实现
│   │   └─ sqlite_storage.py # SQLite 存储实现
│   ├─ utils/                # 工具模块
│   │   ├─ __init__.py
│   │   └─ data_fetcher.py   # 数据获取工具
│   ├─ analysis/             # 数据分析模块
│   │   ├─ __init__.py
│   │   ├─ analyzer.py        # OHLC 数据分析器
│   │   ├─ ai_indicator_generator.py # AI 指标生成器
│   │   ├─ ai_indicator_runner.py   # AI 指标运行器
│   │   └─ indicators.py     # 预定义指标库
│   └─ __init__.py
```

## 安装

1. 创建并激活虚拟环境：

```bash
conda create -n eth_beijing python=3.10
conda activate eth_beijing
# 或者使用 mamba
# mamba create -n eth_beijing python=3.10
# mamba activate eth_beijing
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 获取 OHLC 数据

```bash
python main.py fetch --network eth --pool 0x60594a405d53811d3bc4766596efd80fd545a270 --timeframe day --aggregate 1 --days 7
```

参数说明：
- `--network`: 网络 ID，例如 eth, bsc
- `--pool`: 池子地址
- `--timeframe`: 时间周期，可选 day, hour, minute
- `--aggregate`: 聚合周期，例如 timeframe=minute, aggregate=15 表示 15分钟K线
- `--days`: 回溯天数
- `--storage`: 存储类型，可选 csv, sqlite, both
- `--data-dir`: 数据目录

### 使用 AI 生成技术指标

```bash
python main.py ai-indicator --network eth --pool 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640 --description "创建一个指标，当价格突破20日均线且成交量增加50%时发出买入信号，当价格跌破均线时发出卖出信号" --name "均线突破信号" --plot --save
```

参数说明:
- `--network`: 网络 ID，例如 eth, bsc
- `--pool`: 池子地址
- `--timeframe`: 时间周期（day/hour/minute），默认为 day
- `--aggregate`: 聚合周期，默认为 1
- `--description`: 指标的自然语言描述（可以使用中文或英文）
- `--name`: 指标名称
- `--api-key`: OpenAI API 密钥（也可以通过环境变量 OPENAI_API_KEY 设置）
- `--model`: 要使用的 OpenAI 模型，默认为 gpt-4o
- `--plot`: 绘制并显示图表
- `--save`: 保存生成的指标代码
- `--output-dir`: 指标代码保存目录，默认为 indicators
- `--save-chart`: 保存图表
- `--chart-dir`: 图表保存目录，默认为 charts

#### AI 指标生成示例

以下是一些可以尝试的自然语言指标描述示例:

1. **均线突破策略**:
   ```
   创建一个双均线交叉指标，当5日均线上穿20日均线时产生买入信号，下穿时产生卖出信号
   ```

2. **RSI 超买超卖策略**:
   ```
   当RSI低于30时产生买入信号，高于70时产生卖出信号
   ```

3. **布林带突破策略**:
   ```
   当价格突破布林带上轨且成交量增加时产生买入信号，跌破下轨时产生卖出信号
   ```

4. **MACD 金叉死叉策略**:
   ```
   当MACD线上穿信号线产生金叉时发出买入信号，当MACD线下穿信号线产生死叉时发出卖出信号
   ```

5. **自定义复合策略**:
   ```
   创建一个复合指标，结合RSI和布林带，当RSI低于30且价格接近布林带下轨时产生买入信号，当RSI高于70且价格接近布林带上轨时产生卖出信号
   ```

### 列出已生成的指标

```bash
python main.py list-indicators
```

参数说明:
- `--dir`: 指标代码目录，默认为 indicators
- `--detail`: 显示指标的详细信息，包括代码
- `--filter`: 按关键词过滤指标

示例:
```bash
# 列出所有指标
python main.py list-indicators

# 显示详细信息
python main.py list-indicators --detail

# 按关键词过滤
python main.py list-indicators --filter "均线"
```

### 使用已保存的指标

```bash
python main.py use-indicator --network eth --pool 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640 --indicator "均线突破信号" --plot
```

参数说明:
- `--network`: 网络 ID，例如 eth, bsc
- `--pool`: 池子地址
- `--timeframe`: 时间周期（day/hour/minute），默认为 day
- `--aggregate`: 聚合周期，默认为 1
- `--indicator`: 指标名称或文件名（可以是部分名称，系统会自动匹配最相关的指标）
- `--indicators-dir`: 指标代码目录，默认为 indicators
- `--storage`: 存储类型，默认为 sqlite
- `--data-dir`: 数据目录，默认为 data
- `--plot`: 绘制并显示图表
- `--save-chart`: 保存图表
- `--chart-dir`: 图表保存目录，默认为 charts

示例:
```bash
# 使用指标名称
python main.py use-indicator --network eth --pool 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640 --indicator "均线突破" --plot

# 使用指标文件名
python main.py use-indicator --network eth --pool 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640 --indicator "moving_average_crossover.py" --plot --save-chart
```

### 分析 OHLC 数据

```bash
python main.py analyze --network eth --pool 0x60594a405d53811d3bc4766596efd80fd545a270 --timeframe day --aggregate 1 --save-chart
```

参数说明：
- `--network`: 网络 ID
- `--pool`: 池子地址
- `--timeframe`: 时间周期
- `--aggregate`: 聚合周期
- `--storage`: 存储类型，可选 csv, sqlite
- `--indicators`: 要分析的指标，可选 macd, rsi, volatility
- `--save-chart`: 保存图表
- `--chart-dir`: 图表目录

### 搜索池子

```bash
python main.py search --network eth --query "WETH/USDC"
```

参数说明：
- `--network`: 网络 ID
- `--query`: 搜索关键词

### 列出已存储的数据

```bash
python main.py list --storage sqlite --network eth
```

参数说明：
- `--storage`: 存储类型，可选 csv, sqlite
- `--network`: 网络 ID，如果不指定则列出所有网络

## 示例代码

### 使用 API 客户端获取 OHLC 数据

```python
from geckoterminal_backtracker.api.gecko_api import GeckoTerminalAPI

api = GeckoTerminalAPI()
df = api.get_ohlc(
    network="eth",
    pool_address="0x60594a405d53811d3bc4766596efd80fd545a270",
    timeframe="day",
    aggregate=1,
    limit=100
)

print(df.head())
```

### 使用数据获取器获取并存储历史数据

```python
from geckoterminal_backtracker.utils.data_fetcher import OHLCDataFetcher
from geckoterminal_backtracker.storage.csv_storage import CSVStorage
from geckoterminal_backtracker.storage.sqlite_storage import SQLiteStorage

fetcher = OHLCDataFetcher()
csv_storage = CSVStorage("data")
sqlite_storage = SQLiteStorage("data/geckoterminal_data.db")

df = fetcher.fetch_and_store(
    network="eth",
    pool_address="0x60594a405d53811d3bc4766596efd80fd545a270",
    timeframe="day",
    aggregate=1,
    days_back=30,
    storage_handlers=[csv_storage, sqlite_storage]
)
```

### 使用分析器分析数据

```python
from geckoterminal_backtracker.analysis.ohlc_analysis import OHLCAnalyzer
from geckoterminal_backtracker.storage.sqlite_storage import SQLiteStorage

storage = SQLiteStorage("data/geckoterminal_data.db")
df = storage.load_ohlc(
    network="eth",
    pool_address="0x60594a405d53811d3bc4766596efd80fd545a270",
    timeframe="day",
    aggregate=1
)

analyzer = OHLCAnalyzer(df)
df_with_indicators = analyzer.calculate_indicators()
stats = analyzer.get_summary_stats()
analyzer.plot_price_chart(save_path="charts/price_chart.png")
analyzer.plot_indicators(save_path="charts/indicators_chart.png")
```

## API 限制

GeckoTerminal 免费 API 限制为每分钟 30 次请求。如果需要更高的请求频率，可以考虑订阅 CoinGecko API 的付费计划。

## 许可证

MIT
