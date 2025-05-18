#!/usr/bin/env python
"""
GeckoTerminal 链上数据回溯系统
主程序入口
"""

import os
import sys
import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

from backtest_utils.geckoterminal_backtracker.storage.csv_storage import CSVStorage
from backtest_utils.geckoterminal_backtracker.storage.sqlite_storage import SQLiteStorage
from backtest_utils.geckoterminal_backtracker.api.gecko_api import GeckoTerminalAPI
from backtest_utils.geckoterminal_backtracker.utils.data_fetcher import OHLCDataFetcher
from backtest_utils.geckoterminal_backtracker.analysis.analyzer import OHLCAnalyzer
from backtest_utils.geckoterminal_backtracker.analysis.ai_indicator_runner import generate_ai_indicator
from backtest_utils.geckoterminal_backtracker.analysis.indicator_backtester import (
    find_indicator_file, use_indicator, backtest_indicators, 
    calculate_trading_stats, plot_backtest_results, resample_ohlc
)
from backtest_utils.geckoterminal_backtracker.analysis.indicator_manager import list_indicators, print_indicators_table


def setup_argparse():
    """设置命令行参数解析"""
    parser = argparse.ArgumentParser(description='GeckoTerminal 链上数据回溯系统')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 获取数据命令
    fetch_parser = subparsers.add_parser('fetch', help='获取历史 OHLC 数据')
    fetch_parser.add_argument('--network', required=True, help='网络 ID，例如 eth, bsc')
    fetch_parser.add_argument('--pool', required=True, help='池子地址')
    fetch_parser.add_argument('--timeframe', default='day', choices=['day', 'hour', 'minute'], help='时间周期')
    fetch_parser.add_argument('--aggregate', type=int, default=1, help='聚合周期')
    fetch_parser.add_argument('--days', type=int, default=30, help='回溯天数')
    fetch_parser.add_argument('--storage', default='both', choices=['csv', 'sqlite', 'both'], help='存储类型')
    fetch_parser.add_argument('--data-dir', default='data', help='数据目录')
    
    # AI 指标生成命令
    ai_parser = subparsers.add_parser('ai-indicator', help='使用自然语言生成技术指标')
    ai_parser.add_argument('--description', required=True, help='指标的自然语言描述')
    ai_parser.add_argument('--name', required=True, help='指标名称')
    ai_parser.add_argument('--save', action='store_true', help='保存生成的指标代码')
    ai_parser.add_argument('--output-dir', default='indicators', help='指标代码保存目录')
    ai_parser.add_argument('--api-key', help='OpenAI API 密钥，如果不提供将使用环境变量 OPENAI_API_KEY')
    ai_parser.add_argument('--model', default='gpt-4o', help='要使用的 OpenAI 模型')
    
    # 搜索池子命令
    search_parser = subparsers.add_parser('search', help='搜索池子')
    search_parser.add_argument('--network', required=True, help='网络 ID，例如 eth, bsc')
    search_parser.add_argument('--query', required=True, help='搜索关键词')
    
    # 列出指标命令
    list_indicators_parser = subparsers.add_parser('list-indicators', help='列出所有已保存的指标')
    list_indicators_parser.add_argument('--dir', default='indicators', help='指标代码目录')
    list_indicators_parser.add_argument('--detail', action='store_true', help='显示详细信息')
    list_indicators_parser.add_argument('--filter', help='按关键词过滤指标')
    
    # 使用指标命令
    use_indicator_parser = subparsers.add_parser('use-indicator', help='使用已保存的指标')
    use_indicator_parser.add_argument('--network', required=True, help='网络 ID，例如 eth, bsc')
    use_indicator_parser.add_argument('--pool', required=True, help='池子地址')
    use_indicator_parser.add_argument('--timeframe', default='day', choices=['day', 'hour', 'minute'], help='时间周期')
    use_indicator_parser.add_argument('--aggregate', type=int, default=1, help='聚合周期')
    use_indicator_parser.add_argument('--indicator', required=True, help='指标名称或文件名，用于买入信号')
    use_indicator_parser.add_argument('--sell-indicator', help='用于卖出信号的指标名称或文件名，如果不指定则使用同一个指标')
    use_indicator_parser.add_argument('--buy-column', help='买入信号列名，如果不指定则自动识别')
    use_indicator_parser.add_argument('--sell-column', help='卖出信号列名，如果不指定则自动识别')
    use_indicator_parser.add_argument('--indicators-dir', default='indicators', help='指标代码目录')
    use_indicator_parser.add_argument('--storage', default='sqlite', choices=['csv', 'sqlite'], help='存储类型')
    use_indicator_parser.add_argument('--data-dir', default='data', help='数据目录')
    use_indicator_parser.add_argument('--plot', action='store_true', help='绘制并显示图表')
    use_indicator_parser.add_argument('--save-chart', action='store_true', help='保存图表')
    use_indicator_parser.add_argument('--chart-dir', default='charts', help='图表保存目录')
    use_indicator_parser.add_argument('--save-json', action='store_true', help='保存图表为 JSON 格式')
    use_indicator_parser.add_argument('--json-dir', default='json_charts', help='JSON 图表保存目录')
    use_indicator_parser.add_argument('--resample', help='重新采样数据的时间周期，例如 15min, 1h, 4h, 1d 等')
    
    # 列出已存储数据命令
    list_parser = subparsers.add_parser('list', help='列出已存储的数据')
    list_parser.add_argument('--storage', default='sqlite', choices=['csv', 'sqlite'], help='存储类型')
    list_parser.add_argument('--data-dir', default='data', help='数据目录')
    list_parser.add_argument('--network', help='网络 ID，如果不指定则列出所有网络')
    
    return parser


def fetch_data(args):
    """获取历史 OHLC 数据"""
    print(f"获取 {args.network} 网络上 {args.pool} 池子的 {args.timeframe}_{args.aggregate} OHLC 数据...")
    
    # 创建存储处理器
    storage_handlers = []
    if args.storage in ['csv', 'both']:
        storage_handlers.append(CSVStorage(args.data_dir))
    if args.storage in ['sqlite', 'both']:
        storage_handlers.append(SQLiteStorage(os.path.join(args.data_dir, 'geckoterminal_data.db')))
    
    # 创建数据获取器
    fetcher = OHLCDataFetcher()
    
    # 获取并存储数据
    df = fetcher.fetch_and_store(
        network=args.network,
        pool_address=args.pool,
        timeframe=args.timeframe,
        aggregate=args.aggregate,
        days_back=args.days,
        storage_handlers=storage_handlers
    )
    
    if df.empty:
        print("未找到数据")
        return
    
    print(f"成功获取 {len(df)} 条数据，时间范围: {df['datetime'].min()} 到 {df['datetime'].max()}")
    
    # 显示数据摘要
    print("\n数据摘要:")
    print(f"开盘价 (首个): {df['open'].iloc[0]}")
    print(f"收盘价 (最新): {df['close'].iloc[-1]}")
    print(f"价格变化: {df['close'].iloc[-1] - df['open'].iloc[0]} ({(df['close'].iloc[-1] / df['open'].iloc[0] - 1) * 100:.2f}%)")
    print(f"最高价: {df['high'].max()}")
    print(f"最低价: {df['low'].min()}")
    print(f"总成交量: {df['volume'].sum()}")
    print(f"平均成交量: {df['volume'].mean()}")


def search_pools(args):
    """搜索池子"""
    print(f"在 {args.network} 网络上搜索 '{args.query}'...")
    
    # 创建 API 客户端
    api = GeckoTerminalAPI()
    
    # 搜索池子
    pools = api.search_pools(args.network, args.query)
    
    if not pools:
        print("未找到匹配的池子")
        return
    
    # 显示结果
    print(f"\n找到 {len(pools)} 个匹配的池子:")
    for i, pool in enumerate(pools, 1):
        attrs = pool.get('attributes', {})
        name = attrs.get('name', 'Unknown')
        address = attrs.get('address', 'Unknown')
        base_price = attrs.get('base_token_price_usd', 'Unknown')
        
        print(f"{i}. {name}")
        print(f"   地址: {address}")
        print(f"   价格: ${base_price}")
        
        # 显示交易量信息
        volume = attrs.get('volume_usd', {})
        if volume:
            h1 = volume.get('h1', 'Unknown')
            h24 = volume.get('h24', 'Unknown')
            print(f"   1小时成交量: ${h1}")
            print(f"   24小时成交量: ${h24}")
        
        print()


def list_data(args):
    """列出已存储的数据"""
    if args.storage == 'csv':
        storage = CSVStorage(args.data_dir)
        data_list = storage.list_available_data()
        
        if not data_list:
            print("未找到已存储的数据")
            return
        
        # 过滤网络
        if args.network:
            data_list = [item for item in data_list if item['network'] == args.network]
        
        # 显示结果
        print(f"\n找到 {len(data_list)} 条已存储的数据:")
        for i, item in enumerate(data_list, 1):
            print(f"{i}. 网络: {item['network']}")
            print(f"   池子: {item['pool_address']}")
            print(f"   时间周期: {item['timeframe']}_{item['aggregate']}")
            print()
    else:
        storage = SQLiteStorage(os.path.join(args.data_dir, 'geckoterminal_data.db'))
        
        if args.network:
            pools = storage.get_available_pools(args.network)
            
            if not pools:
                print(f"在 {args.network} 网络上未找到已存储的数据")
                return
            
            print(f"\n在 {args.network} 网络上找到 {len(pools)} 个池子:")
            for i, pool in enumerate(pools, 1):
                print(f"{i}. {pool['name']} ({pool['pool_address']})")
                
                # 显示可用的时间周期
                timeframes = storage.get_available_timeframes(pool['network'], pool['pool_address'])
                print(f"   可用时间周期: {', '.join([tf['name'] for tf in timeframes])}")
                print()
        else:
            networks = storage.get_available_networks()
            
            if not networks:
                print("未找到已存储的数据")
                return
            
            print(f"\n找到 {len(networks)} 个网络:")
            for i, network in enumerate(networks, 1):
                pools = storage.get_available_pools(network)
                print(f"{i}. {network} ({len(pools)} 个池子)")
            
            print("\n使用 --network 参数查看特定网络的池子")


def list_indicators_cmd(args):
    """
    列出所有已保存的指标
    
    参数:
        args: 命令行参数
    """
    indicators = list_indicators(args.dir, args.detail, args.filter)
    print_indicators_table(indicators)
    
    if args.detail and indicators:
        print("\n要查看指标代码，请使用 --detail 参数")
        for ind in indicators:
            if args.filter and (args.filter.lower() in ind['name'].lower() or args.filter.lower() in ind.get('description', '').lower()):
                print(f"\n{'-' * 80}")
                print(f"\n指标名称: {ind['name']}")
                print(f"\n文件路径: {ind['path']}")
                print(f"\n创建时间: {ind.get('created_at', '')}")
                print(f"\n描述: {ind.get('description', '')}")
                print(f"\n代码:\n{ind.get('code', '')}")
                print(f"\n{'-' * 80}")


def use_indicator_cmd(args):
    """
    使用已保存的指标
    
    参数:
        args: 命令行参数
    """
    # 初始化存储
    if args.storage == 'csv':
        storage = CSVStorage(args.data_dir)
    else:
        storage = SQLiteStorage(args.data_dir)
    
    # 检查指标是否存在
    indicator_file = find_indicator_file(args.indicator, args.indicators_dir)
    if not indicator_file:
        print(f"错误: 找不到指标 '{args.indicator}'")
        print("请使用 'list-indicators' 命令查看可用的指标")
        return
    
    print(f"使用指标: {os.path.basename(indicator_file)}")
    
    # 加载 OHLC 数据
    try:
        # Pass the file_path to load_ohlc if it exists in args
        file_path = getattr(args, 'file_path', None)
        df = storage.load_ohlc(args.network, args.pool, args.timeframe, args.aggregate, file_path=file_path)
        if df.empty:
            print(f"错误: 找不到数据。请先使用 'fetch' 命令获取数据")
            return
            
        # 如果是分钟级数据且数据量过大，自动采样或使用用户指定的时间周期重新采样
        if args.timeframe == 'minute' and len(df) > 1000:
            if args.resample:
                # 使用用户指定的时间周期重新采样
                original_len = len(df)
                df = resample_ohlc(df, args.resample)
                print(f"数据已重新采样为 {args.resample} 周期，从 {original_len} 个数据点减少到 {len(df)} 个")
            else:
                # 根据数据量自动选择采样周期
                original_len = len(df)
                if len(df) > 10000:
                    df = resample_ohlc(df, '4h')
                    print(f"数据量过大，已自动采样为 4小时周期，从 {original_len} 个数据点减少到 {len(df)} 个")
                elif len(df) > 5000:
                    df = resample_ohlc(df, '1h')
                    print(f"数据量过大，已自动采样为 1小时周期，从 {original_len} 个数据点减少到 {len(df)} 个")
                elif len(df) > 1000:
                    df = resample_ohlc(df, '15min')
                    print(f"数据量过大，已自动采样为 15分钟周期，从 {original_len} 个数据点减少到 {len(df)} 个")
    except Exception as e:
        print(f"加载数据时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # 应用指标并回测
    try:
        # 使用 backtest_indicators 函数进行回测
        result_df, buy_indicator_info, sell_indicator_info, stats, buy_signal_columns, sell_signal_columns = backtest_indicators(
            df, 
            args.indicator, 
            args.sell_indicator, 
            args.buy_column, 
            args.sell_column, 
            args.indicators_dir
        )
        
        # 显示指标信息
        print(f"成功应用买入指标: {buy_indicator_info['name']}")
        print(f"描述: {buy_indicator_info['description']}")
        print(f"新增列: {', '.join(buy_indicator_info['new_columns'])}")
        
        if sell_indicator_info:
            print(f"\n成功应用卖出指标: {sell_indicator_info['name']}")
            print(f"描述: {sell_indicator_info['description']}")
            print(f"新增列: {', '.join(sell_indicator_info['new_columns'])}")
        
        # 显示信号列信息
        print(f"\n使用的买入信号列: {buy_signal_columns if buy_signal_columns else '未找到'}")
        print(f"使用的卖出信号列: {sell_signal_columns if sell_signal_columns else '未找到'}")
        
        # 显示交易统计信息
        if stats['has_signals']:
            print("\n交易统计:")
            print(f"交易次数: {stats['total_trades']}")
            print(f"盈利交易: {stats['profitable_trades']}")
            print(f"胜率: {stats['win_rate']:.2f}%")
            print(f"总收益率: {stats['total_return']:.2f}%")
            print(f"平均收益率: {stats['avg_return']:.2f}%")
            
            # 显示每笔交易详情
            if stats['trades']:
                print("\n交易详情:")
                print("{:<20} {:<20} {:<10} {:<10} {}".format("买入时间", "卖出时间", "买入价格", "卖出价格", "收益率"))
                for trade in stats['trades']:
                    buy_time = trade['buy_time']
                    sell_time = trade['sell_time']
                    buy_price = trade['buy_price']
                    sell_price = trade['sell_price']
                    profit = trade['profit']
                    profit_str = f"{profit:.2f}%" if profit >= 0 else f"{profit:.2f}%"
                    print("{:<20} {:<20} {:<10.6f} {:<10.6f} {}".format(
                        buy_time.strftime("%Y-%m-%d %H:%M"), 
                        sell_time.strftime("%Y-%m-%d %H:%M"),
                        buy_price, 
                        sell_price,
                        profit_str
                    ))
        else:
            print("\n未检测到有效的交易信号对")
    
    except Exception as e:
        print(f"应用指标时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # 绘制图表
    if args.plot or args.save_chart:
        # 准备保存路径
        chart_path = None
        if args.save_chart:
            os.makedirs(args.chart_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 生成图表名称
            if sell_indicator_info:
                chart_name = f"{args.network}_{args.pool}_{buy_indicator_info['name']}_and_{sell_indicator_info['name']}_{timestamp}.png"
            else:
                chart_name = f"{args.network}_{args.pool}_{buy_indicator_info['name']}_{timestamp}.png"
                
            chart_path = os.path.join(args.chart_dir, chart_name)
        
        # 生成图表标题
        if sell_indicator_info:
            title = f"{buy_indicator_info['name']} (买入) + {sell_indicator_info['name']} (卖出) - {args.network.upper()} {args.pool}"
        else:
            title = f"{buy_indicator_info['name']} - {args.network.upper()} {args.pool}"
        
        # 准备 JSON 保存路径
        json_path = None
        if args.save_json:
            os.makedirs(args.json_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 生成 JSON 文件名
            if sell_indicator_info:
                json_name = f"{args.network}_{args.pool}_{buy_indicator_info['name']}_and_{sell_indicator_info['name']}_{timestamp}.json"
            else:
                json_name = f"{args.network}_{args.pool}_{buy_indicator_info['name']}_{timestamp}.json"
                
            json_path = os.path.join(args.json_dir, json_name)
        
        # 使用 plot_backtest_results 函数绘制图表
        fig = plot_backtest_results(
            result_df, 
            buy_indicator_info, 
            sell_indicator_info, 
            buy_signal_columns, 
            sell_signal_columns,
            title=title,
            save_path=chart_path,
            save_json=json_path,
            network=args.network,
            pool=args.pool,
            timeframe=args.timeframe,
            aggregate=args.aggregate
        )
        
        # 如果设置了 plot 参数但没有设置 save_path，显示图表
        if args.plot and not args.save_chart:
            plt.show()
        
        if chart_path:
            print(f"图表已保存到: {chart_path}")
        
        return fig

def main():
    """主函数"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if args.command == 'fetch':
        fetch_data(args)
    elif args.command == 'search':
        search_pools(args)
    elif args.command == 'list':
        list_data(args)
    elif args.command == 'ai-indicator':
        generate_ai_indicator(args)
    elif args.command == 'list-indicators':
        list_indicators_cmd(args)
    elif args.command == 'use-indicator':
        use_indicator_cmd(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
