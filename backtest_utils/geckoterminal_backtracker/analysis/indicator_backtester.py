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
    回测指标组合
    
    参数:
        df: 原始数据框
        buy_indicator: 买入指标名称或文件名
        sell_indicator: 卖出指标名称或文件名，如果不提供则使用买入指标
        buy_column: 买入信号列名，如果不提供则自动识别
        sell_column: 卖出信号列名，如果不提供则自动识别
        indicators_dir: 指标目录
        use_existing_indicators: 是否使用已应用到DataFrame的指标，跳过文件查找
        
    返回:
        (result_df, buy_indicator_info, sell_indicator_info, stats): 结果数据框、买入指标信息、卖出指标信息、统计信息
    """
    if use_existing_indicators:
        # 使用已经应用到DataFrame的指标，跳过文件查找
        print(f"使用已应用的指标，跳过文件查找")
        result_df = df.copy()
        
        # 创建买入指标信息
        buy_indicator_info = {
            'name': buy_indicator,
            'path': 'database',
            'code': 'stored_in_database',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'new_columns': [col for col in result_df.columns if 'buy' in col.lower() or 'signal' in col.lower()]
        }
        
        # 创建卖出指标信息
        sell_indicator_info = None
        if sell_indicator:
            sell_indicator_info = {
                'name': sell_indicator,
                'path': 'database', 
                'code': 'stored_in_database',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'new_columns': [col for col in result_df.columns if 'sell' in col.lower()]
            }
    else:
        # 原有的文件查找逻辑
        # 应用买入指标
        result_df, buy_indicator_info = use_indicator(df, buy_indicator, indicators_dir)
        
        # 保存买入指标的买入信号
        buy_signal_backup = None
        if 'buy_signal' in result_df.columns:
            buy_signal_backup = result_df['buy_signal'].copy()
            print(f"备份买入信号，共有 {buy_signal_backup.sum()} 个买入信号")
        
        # 如果指定了卖出指标，则应用卖出指标
        sell_indicator_info = None
        if sell_indicator:
            # 保存买入指标的列
            buy_columns = buy_indicator_info['new_columns']
            
            # 应用卖出指标
            result_df, sell_indicator_info = use_indicator(df, sell_indicator, indicators_dir)
            
            # 恢复买入信号
            if buy_signal_backup is not None:
                # 如果卖出指标也创建了buy_signal列，合并两个信号
                if 'buy_signal' in result_df.columns:
                    # 使用逻辑或合并买入信号
                    result_df['buy_signal'] = (result_df['buy_signal'] | buy_signal_backup).astype(int)
                    print(f"合并后的买入信号数量: {result_df['buy_signal'].sum()}")
                else:
                    result_df['buy_signal'] = buy_signal_backup
            
            # 将买入指标的其他列添加回结果中
            for col in buy_columns:
                if col not in result_df.columns and col != 'buy_signal':
                    # 从原始结果中获取买入指标列
                    tmp_df, _ = use_indicator(df, buy_indicator, indicators_dir)
                    result_df[col] = tmp_df[col]
    
    # 提取信号列
    if buy_column and buy_column in result_df.columns:
        # 用户指定了买入信号列
        buy_signal_columns = [buy_column]
    else:
        # 自动识别买入信号列
        buy_signal_columns = [col for col in result_df.columns if 'buy' in col.lower() or ('signal' in col.lower() and result_df[col].dtype in ['int64', 'int32', 'bool'])]
    
    if sell_column and sell_column in result_df.columns:
        # 用户指定了卖出信号列
        sell_signal_columns = [sell_column]
    else:
        # 自动识别卖出信号列
        sell_signal_columns = [col for col in result_df.columns if 'sell' in col.lower()]
    
    # 打印最终的买入和卖出信号数量
    for col in buy_signal_columns:
        if col in result_df.columns:
            print(f"最终 {col} 信号数量: {result_df[col].sum()}")
    
    for col in sell_signal_columns:
        if col in result_df.columns:
            print(f"最终 {col} 信号数量: {result_df[col].sum()}")
    
    # 计算交易统计
    stats = calculate_trading_stats(result_df, buy_signal_columns, sell_signal_columns)
    
    print(f"[DEBUG] 交易统计计算完成:")
    print(f"[DEBUG] - 有信号: {stats['has_signals']}")
    print(f"[DEBUG] - 交易次数: {stats['total_trades']}")
    print(f"[DEBUG] - 胜率: {stats['win_rate']:.2f}%")
    print(f"[DEBUG] - DataFrame包含cumulative_pnl: {'cumulative_pnl' in result_df.columns}")
    print(f"[DEBUG] - DataFrame包含pnl_percentage: {'pnl_percentage' in result_df.columns}")
    
    return result_df, buy_indicator_info, sell_indicator_info, stats, buy_signal_columns, sell_signal_columns

def calculate_trading_stats(df, buy_signal_columns, sell_signal_columns):
    """
    计算交易统计
    
    参数:
        df: 数据框
        buy_signal_columns: 买入信号列
        sell_signal_columns: 卖出信号列
        
    返回:
        stats: 统计信息字典
    """
    print(f"[DEBUG] 开始计算交易统计...")
    print(f"[DEBUG] 买入信号列: {buy_signal_columns}")
    print(f"[DEBUG] 卖出信号列: {sell_signal_columns}")
    
    # 🎯 计算MACD指标
    print(f"[DEBUG] 开始计算MACD指标...")
    
    if 'close' in df.columns and len(df) >= 26:  # 确保有足够的数据计算MACD
        # 计算EMA12和EMA26
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        
        print("ema12", ema12)
        print("ema26", ema26)
        
        # 计算MACD线 (DIF)
        df['macd'] = ema12 - ema26
        
        # 计算信号线 (DEA) - MACD的9日EMA
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        print("macd", df['macd'])
        print("macd_signal", df['macd_signal'])
        
        # 计算MACD柱状图 (MACD Histogram)
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        print("macd_histogram", df['macd_histogram'])
        
        print(f"✅ MACD指标计算完成:")
        print(f"   - MACD范围: {df['macd'].min():.6f} 到 {df['macd'].max():.6f}")
        print(f"   - Signal范围: {df['macd_signal'].min():.6f} 到 {df['macd_signal'].max():.6f}")
        print(f"   - Histogram范围: {df['macd_histogram'].min():.6f} 到 {df['macd_histogram'].max():.6f}")
    else:
        print(f"⚠️ 数据不足，无法计算MACD指标 (需要至少26个数据点，当前: {len(df)})")
    
    stats = {
        'has_signals': False,
        'total_trades': 0,
        'profitable_trades': 0,
        'win_rate': 0,
        'total_return': 0,
        'avg_return': 0,
        'trades': []
    }
    
    # 初始化累计PnL列
    df['cumulative_pnl'] = 1000.0  # 初始投资1000
    df['pnl_percentage'] = 0.0
    
    if not buy_signal_columns or (not sell_signal_columns and len(buy_signal_columns) == 0):
        print(f"[DEBUG] 没有有效的信号列，返回空统计")
        return stats
    
    # 如果没有明确的卖出信号，使用买入信号的反转作为卖出信号
    if not sell_signal_columns and len(buy_signal_columns) > 0:
        buy_signal_col = buy_signal_columns[0]
        print(f"[DEBUG] 使用单一买入信号列生成卖出信号: {buy_signal_col}")
        
        # 根据信号类型处理
        if df[buy_signal_col].dtype == 'bool':
            buy_signals = df[df[buy_signal_col] == True].copy()
            # 假设买入后下一个信号为卖出
            sell_signals = pd.DataFrame()
            in_position = False
            
            for idx, row in df.iterrows():
                if row[buy_signal_col] == True and not in_position:
                    in_position = True
                elif in_position:  # 已经持仓，下一个信号作为卖出
                    sell_signals = pd.concat([sell_signals, pd.DataFrame([row])])
                    in_position = False
        else:  # int或其他类型
            buy_signals = df[df[buy_signal_col] == 1].copy()
            sell_signals = df[df[buy_signal_col] == -1].copy() if -1 in df[buy_signal_col].values else pd.DataFrame()
            
            # 如果没有-1信号，则使用类似上面的逻辑
            if sell_signals.empty:
                sell_signals = pd.DataFrame()
                in_position = False
                
                for idx, row in df.iterrows():
                    if row[buy_signal_col] == 1 and not in_position:
                        in_position = True
                    elif in_position:  # 已经持仓，下一个非买入信号作为卖出
                        if row[buy_signal_col] != 1:
                            sell_signals = pd.concat([sell_signals, pd.DataFrame([row])])
                            in_position = False
    else:
        # 使用第一个买入和卖出信号列
        buy_signal_col = buy_signal_columns[0]
        sell_signal_col = sell_signal_columns[0]
        print(f"[DEBUG] 使用独立的买入和卖出信号列: {buy_signal_col}, {sell_signal_col}")
        
        # 处理不同类型的信号
        if df[buy_signal_col].dtype == 'bool':
            buy_signals = df[df[buy_signal_col] == True].copy()
        else:
            buy_signals = df[df[buy_signal_col] == 1].copy()
            
        if df[sell_signal_col].dtype == 'bool':
            sell_signals = df[df[sell_signal_col] == True].copy()
        else:
            sell_signals = df[df[sell_signal_col] == 1].copy()
    
    print(f"[DEBUG] 原始买入信号数量: {len(buy_signals)}")
    print(f"[DEBUG] 原始卖出信号数量: {len(sell_signals)}")
    
    # 实现现货交易逻辑：只有买入后才能卖出
    valid_buy_signals = []
    valid_sell_signals = []
    in_position = False
    entry_price = 0
    
    # 按时间排序所有信号
    all_signals = pd.DataFrame()
    if not buy_signals.empty:
        buy_signals['signal_type'] = 'buy'
        all_signals = pd.concat([all_signals, buy_signals])
    if not sell_signals.empty:
        sell_signals['signal_type'] = 'sell'
        all_signals = pd.concat([all_signals, sell_signals])
    
    # 按时间排序
    if not all_signals.empty:
        all_signals = all_signals.sort_values('datetime')
        print(f"[DEBUG] 总信号数量: {len(all_signals)}")
        
        # 遍历所有信号，模拟交易
        for idx, row in all_signals.iterrows():
            if row['signal_type'] == 'buy' and not in_position:
                # 买入信号，且当前没有持仓
                valid_buy_signals.append(row)
                in_position = True
                entry_price = row['close']
                print(f"[DEBUG] 买入: {row['datetime']}, 价格: {row['close']}")
            elif row['signal_type'] == 'sell' and in_position:
                # 卖出信号，且当前有持仓
                valid_sell_signals.append(row)
                in_position = False
                profit = (row['close'] - entry_price) / entry_price * 100
                print(f"[DEBUG] 卖出: {row['datetime']}, 价格: {row['close']}, 收益: {profit:.2f}%")
    
    print(f"[DEBUG] 有效买入信号数量: {len(valid_buy_signals)}")
    print(f"[DEBUG] 有效卖出信号数量: {len(valid_sell_signals)}")
    
    # 计算交易统计和累计PnL
    if valid_buy_signals and valid_sell_signals:
        stats['has_signals'] = True
        
        # 计算盈利率
        stats['total_trades'] = len(valid_sell_signals)
        stats['profitable_trades'] = sum([s['close'] > b['close'] for s, b in zip(valid_sell_signals, valid_buy_signals)])
        stats['win_rate'] = stats['profitable_trades'] / stats['total_trades'] * 100 if stats['total_trades'] > 0 else 0
        
        # 计算总收益
        returns = []
        for i in range(min(len(valid_buy_signals), len(valid_sell_signals))):
            buy_time = valid_buy_signals[i]['datetime']
            sell_time = valid_sell_signals[i]['datetime']
            buy_price = valid_buy_signals[i]['close']
            sell_price = valid_sell_signals[i]['close']
            profit = (sell_price - buy_price) / buy_price * 100
            
            returns.append(profit)
            stats['trades'].append({
                'buy_time': buy_time,
                'sell_time': sell_time,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'profit': profit
            })
        
        stats['total_return'] = sum(returns)
        stats['avg_return'] = stats['total_return'] / len(returns) if returns else 0
        
        # 🎯 计算累计PnL曲线
        print(f"[DEBUG] 开始计算累计PnL曲线...")
        
        # 创建交易信号时间序列
        trade_signals = []
        for buy_sig in valid_buy_signals:
            trade_signals.append((buy_sig['datetime'], 'buy', buy_sig['close']))
        for sell_sig in valid_sell_signals:
            trade_signals.append((sell_sig['datetime'], 'sell', sell_sig['close']))
        
        # 按时间排序
        trade_signals.sort(key=lambda x: x[0])
        print(f"[DEBUG] 交易信号时间序列长度: {len(trade_signals)}")
        
        # 模拟交易，计算累计PnL
        initial_investment = 1000  # 初始投资
        current_value = initial_investment
        in_position = False
        entry_price = 0
        pnl_data = []  # 存储每次交易完成后的PnL数据
        
        for time, signal_type, price in trade_signals:
            if signal_type == 'buy' and not in_position:
                entry_price = price
                in_position = True
                print(f"[DEBUG] PnL计算 - 买入: {time}, 价格: {price}")
            elif signal_type == 'sell' and in_position:
                # 计算这笔交易的收益
                profit_pct = (price - entry_price) / entry_price
                current_value *= (1 + profit_pct)
                pnl_data.append((time, current_value))
                in_position = False
                print(f"[DEBUG] PnL计算 - 卖出: {time}, 价格: {price}, 账户价值: {current_value:.2f}")
        
        print(f"[DEBUG] PnL数据点数量: {len(pnl_data)}")
        
        # 为DataFrame的每个时间点分配PnL值
        if pnl_data:
            pnl_df = pd.DataFrame(pnl_data, columns=['time', 'value'])
            last_pnl = initial_investment
            
            for i, row in df.iterrows():
                current_time = row['datetime']
                # 找到当前时间之前的最后一个PnL值
                prev_pnl = pnl_df[pnl_df['time'] <= current_time]
                
                if not prev_pnl.empty:
                    last_pnl = prev_pnl.iloc[-1]['value']
                
                df.at[i, 'cumulative_pnl'] = last_pnl
                df.at[i, 'pnl_percentage'] = (last_pnl - initial_investment) / initial_investment * 100
            
            print(f"[DEBUG] 最终账户价值: {last_pnl:.2f}")
            print(f"[DEBUG] 最终收益率: {(last_pnl - initial_investment) / initial_investment * 100:.2f}%")
            print(f"[DEBUG] 累计PnL列已添加到DataFrame")
        else:
            print(f"[DEBUG] 没有PnL数据点，保持初始值")
    else:
        print(f"[DEBUG] 没有有效的交易对，无法计算PnL")
    
    return stats

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
    
    # 生成图表标题
    if not title:
        if sell_indicator_info:
            title = f"{buy_indicator_info['name']} (买入) + {sell_indicator_info['name']} (卖出)"
        else:
            title = f"{buy_indicator_info['name']}"
            
        if network and pool:
            title += f" - {network.upper()} {pool}"
    
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
