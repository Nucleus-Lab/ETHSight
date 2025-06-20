#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指标回测模块
提供指标应用和回测功能
"""

import os
import json
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from .analyzer import OHLCAnalyzer

def resample_ohlc(df, timeframe):
    """
    根据指定的时间周期重新采样OHLC数据
    
    参数:
        df: 原始数据框
        timeframe: 目标时间周期 ('15min', '1h', '4h', '1d'等)
        
    返回:
        重新采样后的数据框
    """
    # 创建副本以避免修改原始数据
    df_copy = df.copy()
    
    # 确保datetime列是索引且为datetime类型
    if 'datetime' in df_copy.columns:
        df_copy['datetime'] = pd.to_datetime(df_copy['datetime'])
        df_copy = df_copy.set_index('datetime')
    
    # 定义聚合方式
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    
    # 对其他列使用最后一个值
    for col in df_copy.columns:
        if col not in ohlc_dict:
            ohlc_dict[col] = 'last'
    
    # 重新采样
    resampled = df_copy.resample(timeframe).agg(ohlc_dict)
    
    # 删除缺失值
    resampled = resampled.dropna()
    
    # 重置索引
    resampled = resampled.reset_index()
    
    return resampled

def find_indicator_file(indicator_name, indicators_dir):
    """
    查找指标文件
    
    参数:
        indicator_name: 指标名称或文件名
        indicators_dir: 指标目录
        
    返回:
        指标文件路径，如果找不到则返回 None
    """
    # 检查目录是否存在
    if not os.path.exists(indicators_dir):
        return None
    
    # 如果提供的是完整路径，直接返回
    if os.path.exists(indicator_name):
        return indicator_name
    
    # 检查是否是文件名
    indicator_file = os.path.join(indicators_dir, indicator_name)
    if os.path.exists(indicator_file):
        return indicator_file
    
    # 添加 .py 后缀再检查
    indicator_file = os.path.join(indicators_dir, f"{indicator_name}.py")
    if os.path.exists(indicator_file):
        return indicator_file
    
    # 查找匹配的文件
    for filename in os.listdir(indicators_dir):
        if filename.endswith('.py'):
            # 检查文件名是否匹配
            if indicator_name.lower() in filename.lower():
                return os.path.join(indicators_dir, filename)
            
            # 检查文件内容是否匹配
            with open(os.path.join(indicators_dir, filename), 'r', encoding='utf-8') as f:
                content = f.read()
                if f'name = "{indicator_name}"' in content or f"name = '{indicator_name}'" in content:
                    return os.path.join(indicators_dir, filename)
    
    return None

def use_indicator(df, indicator_name, indicators_dir):
    """
    使用指标
    
    参数:
        df: 数据框
        indicator_name: 指标名称或文件名
        indicators_dir: 指标目录
        
    返回:
        (result_df, indicator_info): 应用指标后的数据框和指标信息
    """
    # 查找指标文件
    indicator_file = find_indicator_file(indicator_name, indicators_dir)
    if not indicator_file:
        raise ValueError(f"找不到指标: {indicator_name}")
    
    # 读取指标文件
    with open(indicator_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # 提取指标信息
    indicator_info = {
        'name': os.path.splitext(os.path.basename(indicator_file))[0],
        'path': indicator_file,
        'code': code,
        'created_at': datetime.fromtimestamp(os.path.getctime(indicator_file)).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 提取描述
    description_start = code.find('"""')
    if description_start != -1:
        description_end = code.find('"""', description_start + 3)
        if description_end != -1:
            indicator_info['description'] = code[description_start + 3:description_end].strip()
    
    # 创建数据框的副本
    result_df = df.copy()
    
    # 记录原始列
    original_columns = set(result_df.columns)
    
    # 执行指标代码
    exec_globals = {'df': result_df, 'np': np, 'pd': pd}
    try:
        exec(code, exec_globals)
        result_df = exec_globals.get('df', result_df)
    except Exception as e:
        raise RuntimeError(f"执行指标代码时出错: {str(e)}")
    
    # 确定新增列
    new_columns = [col for col in result_df.columns if col not in original_columns]
    indicator_info['new_columns'] = new_columns
    
    return result_df, indicator_info

def use_indicator_code(df, indicator_code, indicator_name):
    """
    使用指标代码直接应用到DataFrame
    
    参数:
        df: 数据框
        indicator_code: 指标代码字符串
        indicator_name: 指标名称
        
    返回:
        (result_df, indicator_info): 应用指标后的数据框和指标信息
    """
    # 创建指标信息
    indicator_info = {
        'name': indicator_name,
        'path': 'database',
        'code': indicator_code,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 创建数据框的副本
    result_df = df.copy()
    
    # 记录原始列
    original_columns = set(result_df.columns)
    
    # 执行指标代码
    exec_globals = {'df': result_df, 'np': np, 'pd': pd}
    try:
        exec(indicator_code, exec_globals)
        result_df = exec_globals.get('df', result_df)
    except Exception as e:
        raise RuntimeError(f"执行指标代码时出错: {str(e)}")
    
    # 确定新增列
    new_columns = [col for col in result_df.columns if col not in original_columns]
    indicator_info['new_columns'] = new_columns
    
    return result_df, indicator_info

def backtest_indicators(df, buy_indicator, sell_indicator=None, buy_column=None, sell_column=None, indicators_dir='indicators', use_existing_indicators=False):
    """
    Backtest with prepared signals
    
    Args:
        df: DataFrame with prepared signals
        buy_indicator: Buy indicator name for display
        sell_indicator: Sell indicator name for display
        buy_column: Buy signal column name (defaults to 'buy_signal')
        sell_column: Sell signal column name (defaults to 'sell_signal')
        indicators_dir: Not used
        use_existing_indicators: Not used
        
    Returns:
        (result_df, buy_indicator_info, sell_indicator_info, stats, buy_signal_columns, sell_signal_columns)
    """
    print(f"Running backtest with prepared signals...")
    result_df = df.copy()
    
    # Use default column names if not specified
    buy_signal_columns = [buy_column] if buy_column else ['buy_signal']
    sell_signal_columns = [sell_column] if sell_column else ['sell_signal']
    
    # Create indicator info
    buy_indicator_info = {
        'name': buy_indicator,
        'path': 'database',
        'code': 'stored_in_database',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'new_columns': buy_signal_columns
    }
    
    sell_indicator_info = None
    if sell_indicator:
        sell_indicator_info = {
            'name': sell_indicator,
            'path': 'database', 
            'code': 'stored_in_database',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'new_columns': sell_signal_columns
        }
    
    # Calculate trading stats
    stats = calculate_trading_stats(result_df, buy_signal_columns, sell_signal_columns)
    
    return result_df, buy_indicator_info, sell_indicator_info, stats, buy_signal_columns, sell_signal_columns

def calculate_trading_stats(df, buy_signal_columns, sell_signal_columns):
    """
    Calculate trading statistics
    
    Args:
        df: DataFrame with signals
        buy_signal_columns: Buy signal column names
        sell_signal_columns: Sell signal column names
        
    Returns:
        stats: Dictionary with trading statistics (JSON serializable)
    """
    print(f"[DEBUG] Starting trading stats calculation...")
    print(f"[DEBUG] Buy signal columns: {buy_signal_columns}")
    print(f"[DEBUG] Sell signal columns: {sell_signal_columns}")
    
    stats = {
        'has_signals': False,
        'total_trades': 0,
        'profitable_trades': 0,
        'win_rate': 0,
        'total_return': 0,
        'avg_return': 0,
        'trades': []
    }
    
    # Initialize cumulative PnL columns
    df['cumulative_pnl'] = 0.0  # In percentage
    df['pnl_percentage'] = 0.0
    
    if not buy_signal_columns or (not sell_signal_columns and len(buy_signal_columns) == 0):
        print(f"[DEBUG] No valid signal columns, returning empty stats")
        return stats
    
    # Use first buy and sell signal columns
    buy_signal_col = buy_signal_columns[0]
    sell_signal_col = sell_signal_columns[0] if sell_signal_columns else None
    
    print(f"[DEBUG] Using signal columns - Buy: {buy_signal_col}, Sell: {sell_signal_col}")
    
    # Create a list to store buy entries with their costs
    buy_entries = []  # List of tuples (entry_time, quantity, cost)
    current_position = 0  # Number of positions held
    total_investment = 0  # Total cost basis
    current_value = 0     # Current value of all positions
    cumulative_pnl = 0    # Cumulative PnL in percentage
    
    # Process all signals chronologically
    for idx, row in df.iterrows():
        current_time = row['datetime']
        current_price = row['close']
        
        # Handle buy signals (can accumulate positions)
        if row[buy_signal_col] == 1:
            current_position += 1
            position_cost = current_price
            total_investment += position_cost
            current_value = current_position * current_price
            
            # Record buy entry
            buy_entries.append({
                'time': current_time,
                'price': position_cost,
                'quantity': 1,
                'remaining': 1  # Track how much of this position remains
            })
            
            print(f"[DEBUG] Buy signal at {current_time}: Position={current_position}, Cost={position_cost}")
            
        # Handle sell signals (can reduce positions)
        elif sell_signal_col and row[sell_signal_col] == 1 and current_position > 0 and buy_entries:
            # Sort buy entries by time to ensure FIFO
            buy_entries.sort(key=lambda x: x['time'])
            
            # Only process sells that have corresponding earlier buys
            valid_buys = [b for b in buy_entries if b['time'] < current_time and b['remaining'] > 0]
            
            if valid_buys:
                # Get the earliest buy with remaining quantity
                buy_entry = valid_buys[0]
                
                # Calculate profit/loss for this specific trade
                entry_price = buy_entry['price']
                trade_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Update position tracking
                buy_entry['remaining'] -= 1
                current_position -= 1
                
                # Update total investment
                if current_position > 0:
                    # Remove this trade's cost from total investment
                    total_investment -= entry_price
                else:
                    total_investment = 0
                
                current_value = current_position * current_price
                cumulative_pnl += trade_pnl_pct
                
                # Record the trade
                stats['trades'].append({
                    'buy_time': buy_entry['time'].isoformat(),
                    'sell_time': current_time.isoformat(),
                    'buy_price': float(entry_price),
                    'sell_price': float(current_price),
                    'profit': float(trade_pnl_pct)
                })
                
                print(f"[DEBUG] Sell signal at {current_time}: Position={current_position}, Value={current_price}, PnL={trade_pnl_pct:.2f}%")
            else:
                print(f"[DEBUG] Ignored sell signal at {current_time} - no valid buy entries found")
            
        # Update current value for open positions
        elif current_position > 0:
            current_value = current_position * current_price
        
        # Calculate and store cumulative PnL percentage
        if total_investment > 0:
            unrealized_pnl_pct = ((current_value - total_investment) / total_investment) * 100
            df.at[idx, 'pnl_percentage'] = cumulative_pnl + unrealized_pnl_pct
        else:
            df.at[idx, 'pnl_percentage'] = cumulative_pnl
            
        df.at[idx, 'cumulative_pnl'] = df.at[idx, 'pnl_percentage']
    
    # Calculate final trading statistics
    completed_trades = len(stats['trades'])
    if completed_trades > 0:
        stats['has_signals'] = True
        stats['total_trades'] = completed_trades
        stats['total_return'] = float(df['pnl_percentage'].iloc[-1])
        stats['avg_return'] = stats['total_return'] / completed_trades
        
        # Count profitable trades
        stats['profitable_trades'] = sum(1 for trade in stats['trades'] if trade['profit'] > 0)
        stats['win_rate'] = (stats['profitable_trades'] / completed_trades) * 100
    
    # Ensure all numeric values are basic Python types (not numpy or pandas types)
    stats = {k: float(v) if isinstance(v, (np.floating, np.integer)) else v 
            for k, v in stats.items()}
    
    print(f"[DEBUG] Final stats: {stats}")
    print(f"[DEBUG] Open positions at end: {current_position}")
    if current_position > 0:
        print(f"[DEBUG] Warning: {current_position} positions still open at end of backtest")
        
    return stats

# def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
#     """
#     Calculate MACD指标
    
#     Args:
#         df: DataFrame with OHLC data
#         fast_period: Fast EMA period (default 12)
#         slow_period: Slow EMA period (default 26)
#         signal_period: Signal EMA period (default 9)
        
#     Returns:
#         df: DataFrame with MACD columns
#     """
#     # 🎯 计算MACD指标
#     print(f"[DEBUG] 开始计算MACD指标...")
    
#     if 'close' in df.columns and len(df) >= 26:  # 确保有足够的数据计算MACD
#         # 计算EMA12和EMA26
#         ema12 = df['close'].ewm(span=12, adjust=False).mean()
#         ema26 = df['close'].ewm(span=26, adjust=False).mean()
         
#         # 计算MACD线 (DIF)
#         df['macd'] = ema12 - ema26
        
#         # 计算信号线 (DEA) - MACD的9日EMA
#         df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
#         # 计算MACD柱状图 (MACD Histogram)
#         df['macd_histogram'] = df['macd'] - df['macd_signal']
        
#         print(f"✅ MACD指标计算完成:")
#         print(f"   - MACD范围: {df['macd'].min():.6f} 到 {df['macd'].max():.6f}")
#         print(f"   - Signal范围: {df['macd_signal'].min():.6f} 到 {df['macd_signal'].max():.6f}")
#         print(f"   - Histogram范围: {df['macd_histogram'].min():.6f} 到 {df['macd_histogram'].max():.6f}")
#     else:
#         print(f"⚠️ 数据不足，无法计算MACD指标 (需要至少26个数据点，当前: {len(df)})")
    
#     return df

def plot_backtest_results(df, buy_indicator_info, sell_indicator_info, buy_signal_columns, sell_signal_columns, 
                         title=None, save_path=None, save_json=None, network=None, pool=None,
                         timeframe='day', aggregate=1):
    """
    绘制回测结果
    
    参数:
        df: 数据框
        buy_indicator_info: 买入指标信息
        sell_indicator_info: 卖出指标信息
        buy_signal_columns: 买入信号列
        sell_signal_columns: 卖出信号列
        title: 图表标题
        save_path: 保存图表路径
        save_json: 保存JSON路径
        network: 网络名称
        pool: 池子地址
    """
    # Prepare df with MACD for plotting
    df = calculate_macd(df)
    
    analyzer = OHLCAnalyzer(df)
    
    # 准备所有指标列用于绘图
    all_indicator_columns = []
    
    # 添加买入信号列
    if buy_signal_columns:
        all_indicator_columns.extend(buy_signal_columns)
    
    # 添加卖出信号列
    if sell_signal_columns:
        all_indicator_columns.extend(sell_signal_columns)
    
    # 添加其他新增列
    if buy_indicator_info and 'new_columns' in buy_indicator_info:
        for col in buy_indicator_info['new_columns']:
            if col not in all_indicator_columns:
                all_indicator_columns.append(col)
    
    if sell_indicator_info and 'new_columns' in sell_indicator_info:
        for col in sell_indicator_info['new_columns']:
            if col not in all_indicator_columns:
                all_indicator_columns.append(col)
                
    # 确保买卖信号列被正确识别为信号指标
    # 在列名中添加"signal"标记以确保它们被正确分类
    if buy_signal_columns:
        for col in buy_signal_columns:
            if col in df.columns and 'signal' not in col.lower() and 'buy' not in col.lower():
                # 创建一个新列，并在列名中添加"signal"
                signal_col_name = f"{col}_buy_signal"
                df[signal_col_name] = df[col]
                all_indicator_columns.append(signal_col_name)
                
    if sell_signal_columns:
        for col in sell_signal_columns:
            if col in df.columns and 'signal' not in col.lower() and 'sell' not in col.lower():
                # 创建一个新列，并在列名中添加"signal"
                signal_col_name = f"{col}_sell_signal"
                df[signal_col_name] = df[col]
                all_indicator_columns.append(signal_col_name)
    
    # 提取信号列
    signal_columns = buy_signal_columns + sell_signal_columns
    signal_indicators = []
    
    # 添加买入信号
    for col in buy_signal_columns:
        signal_indicators.append({
            'name': buy_indicator_info['name'],
            'column': col,
            'signal_type': 'buy'
        })
        
    # 添加卖出信号
    for col in sell_signal_columns:
        indicator_name = sell_indicator_info['name'] if sell_indicator_info else buy_indicator_info['name']
        signal_indicators.append({
            'name': indicator_name,
            'column': col,
            'signal_type': 'sell'
        })
    
    # # 生成图表标题
    # if not title:
    #     if sell_indicator_info:
    #         title = f"{buy_indicator_info['name']} (买入) + {sell_indicator_info['name']} (卖出)"
    #     else:
    #         title = f"{buy_indicator_info['name']}"
            
    #     if network and pool:
    #         title += f" - {network.upper()} {pool}"
    
    # 绘制图表
    fig = analyzer.plot_with_indicators(
        all_indicator_columns,
        title=title,
        save_path=save_path,
        save_json=save_json,
        timeframe=timeframe,
        aggregate=aggregate
    )
    
    return fig

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """
    计算MACD指标
    
    参数:
        df: 数据框
        fast_period: 快速EMA周期 (默认12)
        slow_period: 慢速EMA周期 (默认26)
        signal_period: 信号线EMA周期 (默认9)
        
    返回:
        df: 添加了MACD列的数据框
    """
    print(f"[DEBUG] 计算MACD指标 (EMA{fast_period}, EMA{slow_period}, Signal{signal_period})...")
    
    if 'close' not in df.columns:
        raise ValueError("数据框中缺少 'close' 列")
    
    if len(df) < slow_period:
        print(f"⚠️ 数据不足，无法计算MACD指标 (需要至少{slow_period}个数据点，当前: {len(df)})")
        return df
    
    # 计算快速和慢速EMA
    ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
    
    # 计算MACD线 (DIF)
    df['macd'] = ema_fast - ema_slow
    
    # 计算信号线 (DEA) - MACD的EMA
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    
    # 计算MACD柱状图 (MACD Histogram)
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    print(f"✅ MACD指标计算完成:")
    print(f"   - MACD范围: {df['macd'].min():.4f} 到 {df['macd'].max():.4f}")
    print(f"   - Signal范围: {df['macd_signal'].min():.4f} 到 {df['macd_signal'].max():.4f}")
    print(f"   - Histogram范围: {df['macd_histogram'].min():.4f} 到 {df['macd_histogram'].max():.4f}")
    
    return df
