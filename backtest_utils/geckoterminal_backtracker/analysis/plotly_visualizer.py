"""
Plotly 可视化模块
用于创建交互式图表

支持将图表导出为HTML和JSON格式
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import os
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

def plot_with_indicators(df: pd.DataFrame, indicators: List[str], title: Optional[str] = None, 
                        save_path: Optional[str] = None, show: bool = True, 
                        save_json: Optional[str] = None, timeframe: str = 'day', 
                        aggregate: int = 1) -> go.Figure:
    """
    使用 Plotly 绘制带有指标的交互式图表
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        indicators (list): 要显示的指标列名列表
        title (str, optional): 图表标题
        save_path (str, optional): 保存路径 (HTML 文件)
        show (bool): 是否显示图表
        save_json (str, optional): 保存路径 (JSON 文件)
        timeframe (str, optional): 时间周期 (minute, hour, day)
        aggregate (int, optional): 聚合周期
        
    返回:
        plotly.graph_objects.Figure: Plotly 图表对象
    """
    # 验证指标是否存在
    missing_indicators = [ind for ind in indicators if ind not in df.columns]
    if missing_indicators:
        raise ValueError(f"以下指标不存在于数据中: {', '.join(missing_indicators)}")
    
    # 检查必要的列是否存在
    required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"缺少K线图所需的列: {', '.join(missing_columns)}")
    
    # 分类指标
    signal_indicators = []
    overlay_indicators = []  # 可以叠加在价格图上的指标
    separate_indicators = []  # 需要单独显示的指标
    
    # 强制添加买卖信号列
    if 'buy_signal' in df.columns:
        signal_indicators.append('buy_signal')
    if 'sell_signal' in df.columns:
        signal_indicators.append('sell_signal')
        
    # 打印所有列名以进行调试
    print(f"\n数据框列名: {df.columns.tolist()}")
    
    # 分类其他指标
    for ind in indicators:
        # 跳过已添加的买卖信号列
        if ind in ['buy_signal', 'sell_signal']:
            continue
            
        # 判断是否为信号指标
        if ('signal' in ind.lower() or 'buy' in ind.lower() or 'sell' in ind.lower() or 
            '信号' in ind or '买入' in ind or '卖出' in ind):
            signal_indicators.append(ind)
        elif df[ind].dtype in ['bool', 'int64', 'int32'] and set(df[ind].unique()).issubset({0, 1, True, False}):
            signal_indicators.append(ind)
        # 判断是否可以叠加在价格图上
        elif 'ma' in ind.lower() or 'ema' in ind.lower() or 'sma' in ind.lower() or 'wma' in ind.lower() or \
             'avg' in ind.lower() or 'mean' in ind.lower() or 'support' in ind.lower() or 'resistance' in ind.lower() or \
             'trend' in ind.lower() or 'line' in ind.lower() or 'band' in ind.lower() or \
             '均线' in ind or '支撑' in ind or '压力' in ind or '趋势' in ind:
            overlay_indicators.append(ind)
        else:
            separate_indicators.append(ind)
            
    # 打印信号指标列表，帮助调试
    print(f"\n识别到的信号指标: {signal_indicators}")
    
    # 不自动添加移动平均线或其他指标
    # 只显示用户指定的指标
    
    # 确定子图数量
    n_subplots = 3 + len(separate_indicators)  # 价格 + 成交量 + 累计 PNL + 单独指标

    # 创建子图
    fig = make_subplots(
        rows=n_subplots, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,  # 进一步减小垂直间距
        subplot_titles=['Price & Indicators', 'Volume', '累计收益率 (%)'] + separate_indicators,
        row_heights=[0.7, 0.15, 0.15] + [0.15/(len(separate_indicators) or 1)] * len(separate_indicators)  # 调整高度比例，增加价格图比例
    )
    
    # 设置标题
    if title:
        chart_title = title
    else:
        # 尝试从数据中提取代币信息
        if 'base_token_symbol' in df.columns and 'quote_token_symbol' in df.columns:
            base = df['base_token_symbol'].iloc[0] if not pd.isna(df['base_token_symbol'].iloc[0]) else 'Base'
            quote = df['quote_token_symbol'].iloc[0] if not pd.isna(df['quote_token_symbol'].iloc[0]) else 'Quote'
            chart_title = f"{base}/{quote} Technical Analysis"
        else:
            chart_title = "Technical Analysis"

    # 使用更专业的标题布局
    fig.update_layout(
        title={
            'text': chart_title,
            'x': 0.01,  # 左对齐
            'y': 0.98,
            'xanchor': 'left',
            'yanchor': 'top',
            'font': dict(size=16)
        }
    )
    
    # 添加K线图
    # 计算涨跌幅 - 使用 .loc 避免 Pandas 警告
    df.loc[:, 'change_pct'] = ((df['close'] - df['open']) / df['open'] * 100).round(2)
    
    # 创建悬停文本 - 动态调整小数位数
    hover_texts = []
    
    # 检测价格范围，动态调整小数位数
    min_price = df['low'].min()
    if min_price < 0.0001:
        hover_decimal_places = 10  # 非常小的单位
    elif min_price < 0.01:
        hover_decimal_places = 8   # 很小的单位
    elif min_price < 1:
        hover_decimal_places = 6   # 小单位
    else:
        hover_decimal_places = 4   # 正常单位
    
    for idx, row in df.iterrows():
        hover_text = f"<b>{row['datetime']}</b><br>"
        hover_text += f"开盘: {row['open']:.{hover_decimal_places}f}<br>"
        hover_text += f"最高: {row['high']:.{hover_decimal_places}f}<br>"
        hover_text += f"最低: {row['low']:.{hover_decimal_places}f}<br>"
        hover_text += f"收盘: {row['close']:.{hover_decimal_places}f}<br>"
        hover_text += f"涨跌幅: {row['change_pct']:.2f}%<br>"
        hover_texts.append(hover_text)
    
    fig.add_trace(
        go.Candlestick(
            x=df['datetime'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线',
            increasing=dict(line=dict(color='#00FFEA', width=1.5), fillcolor='#00FFEA'),  # 青色上涨
            decreasing=dict(line=dict(color='#FF5252', width=1.5), fillcolor='#FF5252'),  # 红色下跌
            line=dict(width=1.5),
            whiskerwidth=0.8,  # 影线宽度
        ),
        row=1, col=1
    )
    
    # 处理信号指标
    for signal_ind in signal_indicators:
        buy_signals = pd.DataFrame()
        sell_signals = pd.DataFrame()
        valid_buy_df = pd.DataFrame()
        valid_sell_df = pd.DataFrame()
        # 复制数据
        signal_df = df.copy()
        
        # 根据指标名称和数据类型处理信号
        valid_sell_df = pd.DataFrame()
        if signal_ind == 'buy_signal':
            # 如果是标准买入信号列
            buy_signals = signal_df[signal_df[signal_ind] == 1].copy()
            print(f"buy_signal 列中有 {len(buy_signals)} 个买入信号")
            if not buy_signals.empty:
                print("buy_signals head:\n", buy_signals[['datetime', 'buy_signal']].head())
            if len(buy_signals) > 0:
                valid_buy_df = buy_signals
                print("[DEBUG] valid_buy_df head:\n", valid_buy_df[['datetime', 'buy_signal']].head())
        elif signal_ind == 'sell_signal':
            # 如果是标准卖出信号列
            sell_signals = signal_df[signal_df[signal_ind] == 1].copy()
            print(f"sell_signal 列中有 {len(sell_signals)} 个卖出信号")
            if not sell_signals.empty:
                print("sell_signals head:\n", sell_signals[['datetime', 'sell_signal']].head())
            if len(sell_signals) > 0:
                valid_sell_df = sell_signals
                print("[DEBUG] valid_sell_df head:\n", valid_sell_df[['datetime', 'sell_signal', 'low']].head() if 'low' in valid_sell_df.columns else valid_sell_df.head())

        # 每次循环都尝试添加 trace
        # 计算偏移量，确保信号点不与K线重叠
        price_range = df['high'].max() - df['low'].min()
        buy_offset = price_range * 0.04  # 买点在最高价上方4%
        sell_offset = price_range * 0.04  # 卖点在最高价上方4%

        if not valid_buy_df.empty:
            y_buy = valid_buy_df['high'] + buy_offset if 'high' in valid_buy_df.columns else valid_buy_df.iloc[:, 1]
            fig.add_trace(
                go.Scatter(
                    x=valid_buy_df['datetime'],
                    y=y_buy,
                    mode='markers+text',
                    name=f'Buy Signal ({signal_ind})',
                    text=['B'] * len(valid_buy_df),
                    textposition='middle center',  # 文字居中对齐
                    marker=dict(
                        symbol='circle',
                        size=20,  # 增大圆圈大小
                        color='#00FFEA',
                        line=dict(width=2, color='#00FFEA'),
                        opacity=0.9
                    ),
                    textfont=dict(color='black', size=10, family='Arial Black')
                ),
                row=1, col=1
            )
        if not valid_sell_df.empty:
            # 卖出信号也放在K线上方，但偏移量更大
            y_sell = valid_sell_df['high'] + sell_offset if 'high' in valid_sell_df.columns else valid_sell_df.iloc[:, 1]
            fig.add_trace(
                go.Scatter(
                    x=valid_sell_df['datetime'],
                    y=y_sell,
                    mode='markers+text',
                    name=f'Sell Signal ({signal_ind})',
                    text=['S'] * len(valid_sell_df),
                    textposition='middle center',  # 文字居中对齐
                    marker=dict(
                        symbol='circle',
                        size=20,  # 增大圆圈大小
                        color='#FF5252',
                        line=dict(width=2, color='#FF5252'),
                        opacity=0.9
                    ),
                    textfont=dict(color='black', size=10, family='Arial Black')
                ),
                row=1, col=1
            )
        print('fig traces:', [t.name for t in fig.data])
        
        # 确保信号数据框中包含必要的价格列
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in buy_signals.columns and not buy_signals.empty:
                buy_signals[col] = signal_df.loc[buy_signals.index, col].values
            if col not in sell_signals.columns and not sell_signals.empty:
                sell_signals[col] = signal_df.loc[sell_signals.index, col].values
        
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
            
            # 遍历所有信号，模拟交易
            for idx, row in all_signals.iterrows():
                if row['signal_type'] == 'buy' and not in_position:
                    # 买入信号，且当前没有持仓
                    valid_buy_signals.append(row)
                    in_position = True
                    entry_price = row['close']
                elif row['signal_type'] == 'sell' and in_position:
                    # 卖出信号，且当前有持仓
                    valid_sell_signals.append(row)
                    in_position = False
        
        # 将有效信号转换回 DataFrame
        valid_buy_df = pd.DataFrame(valid_buy_signals) if valid_buy_signals else pd.DataFrame()
        valid_sell_df = pd.DataFrame(valid_sell_signals) if valid_sell_signals else pd.DataFrame()
        
        # 检查有效信号数据框是否包含必要的价格列
        required_columns = ['open', 'high', 'low', 'close', 'datetime']
        
        # 打印调试信息
        if not valid_buy_df.empty:
            print(f"\n有效买入信号数量: {len(valid_buy_df)}")
            print(f"有效买入信号列: {valid_buy_df.columns.tolist()}")
        
        if not valid_sell_df.empty:
            print(f"\n有效卖出信号数量: {len(valid_sell_df)}")
            print(f"有效卖出信号列: {valid_sell_df.columns.tolist()}")
        
        # 计算信号点的位置 - 在蜡烛图的右侧而不是直接在上面
        # 使用价格数据的最小值和最大值来计算偏移量
        price_range = df['high'].max() - df['low'].min()
        offset_factor = 0.003  # 偏移因子，可以调整
        
        # 如果有效买入信号为空或缺少必要列，则跳过
        if valid_buy_df.empty:
            buy_df_offset = pd.DataFrame()
        else:
            # 检查必要列是否存在
            if 'high' not in valid_buy_df.columns:
                print("\n警告: 有效买入信号数据框中缺少 'high' 列，将使用 'close' 列代替")
                valid_buy_df['high'] = valid_buy_df['close'] if 'close' in valid_buy_df.columns else df.loc[valid_buy_df.index, 'close'].values
            
            # 创建买入信号的副本，并将位置偏移到右侧上方
            buy_df_offset = valid_buy_df.copy()
            buy_df_offset['y_position'] = buy_df_offset['high'] + price_range * offset_factor  # 改为上方
        
        # 添加买入信号
        if not valid_buy_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_df_offset['datetime'],
                    y=buy_df_offset['y_position'],  # 使用偏移后的位置
                    mode='markers+text',  
                    name=f'Buy Signal ({signal_ind})',  # 保证唯一
                    text=['B'] * len(buy_df_offset),  # 简化标记为 B
                    textposition='middle center',  # 文本在中间
                    marker=dict(
                        symbol='circle', 
                        size=16,  
                        color='#00FFEA',  # 青色圆圈
                        line=dict(width=2, color='#00FFEA'),  
                        opacity=1.0
                    ),
                    textfont=dict(color='white', size=10, family='Arial Black')
                ),
                row=1, col=1
            )
        
        # 如果有效卖出信号为空或缺少必要列，则跳过
        if valid_sell_df.empty:
            sell_df_offset = pd.DataFrame()
        else:
            # 检查必要列是否存在
            if 'low' not in valid_sell_df.columns:
                print("\n警告: 有效卖出信号数据框中缺少 'low' 列，将使用 'close' 列代替")
                valid_sell_df['low'] = valid_sell_df['close'] if 'close' in valid_sell_df.columns else df.loc[valid_sell_df.index, 'close'].values
            
            # 创建卖出信号的副本，并将位置偏移到右侧下方
            sell_df_offset = valid_sell_df.copy()
            sell_df_offset['y_position'] = sell_df_offset['low'] - price_range * offset_factor  # 改为下方
            
            # 添加卖出信号
            fig.add_trace(
                go.Scatter(
                    x=sell_df_offset['datetime'],
                    y=sell_df_offset['y_position'],  # 使用偏移后的位置
                    mode='markers+text',  
                    name=f'Sell Signal ({signal_ind})',  # 保证唯一
                    text=['S'] * len(sell_df_offset),  # 简化标记为 S
                    textposition='middle center',  # 文本在中间
                    marker=dict(
                        symbol='circle', 
                        size=16,  
                        color='#FF5252',  # 红色圆圈
                        line=dict(width=2, color='#FF5252'),  
                        opacity=1.0
                    ),
                    textfont=dict(color='white', size=10, family='Arial Black')
                ),
                row=1, col=1
            )
        
        # 打印所有 trace 名称，帮助调试
        print('fig traces:', [t.name for t in fig.data])   
        
        # 计算并显示交易统计
        if not valid_buy_df.empty and not valid_sell_df.empty:
            # 计算盈利率
            total_trades = len(valid_sell_df)
            profitable_trades = sum(valid_sell_df['close'].values > valid_buy_df['close'].values[:len(valid_sell_df)])
            win_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0
            
            # 计算总收益
            returns = []
            buy_sell_pairs = []
            
            for i in range(min(len(valid_buy_df), len(valid_sell_df))):
                buy_price = valid_buy_df.iloc[i]['close']
                sell_price = valid_sell_df.iloc[i]['close']
                buy_time = valid_buy_df.iloc[i]['datetime']
                sell_time = valid_sell_df.iloc[i]['datetime']
                returns.append((sell_price - buy_price) / buy_price * 100)
                buy_sell_pairs.append((buy_time, buy_price, sell_time, sell_price))
            
            total_return = sum(returns)
            avg_return = total_return / len(returns) if returns else 0
            
            # 计算累计 PNL 曲线
            df['cumulative_pnl'] = 0.0
            df['pnl_percentage'] = 0.0
            has_pnl_data = False
            
            # 按时间排序买卖点
            all_signals = []
            for i, row in valid_buy_df.iterrows():
                all_signals.append((row['datetime'], 'buy', row['close']))
            for i, row in valid_sell_df.iterrows():
                all_signals.append((row['datetime'], 'sell', row['close']))
            all_signals.sort(key=lambda x: x[0])
            
            # 初始化 PNL 数据
            pnl_data = []
            pnl_times = []
            pnl_values = []
            pnl_percentages = []
            initial_investment = 1000  # 假设初始投资1000
            current_value = initial_investment
            in_position = False
            entry_price = 0
            entry_time = None
            
            # 模拟交易，计算每个时间点的账户价值
            for time, signal_type, price in all_signals:
                if signal_type == 'buy' and not in_position:
                    entry_price = price
                    entry_time = time
                    in_position = True
                elif signal_type == 'sell' and in_position:
                    # 计算这笔交易的收益
                    profit_pct = (price - entry_price) / entry_price
                    current_value *= (1 + profit_pct)
                    pnl_data.append((time, current_value, profit_pct * 100))
                    in_position = False
            
            # 为每个时间点填充 PNL 值
            if pnl_data:
                # 将 PNL 数据转换为 DataFrame 以便于处理
                pnl_df = pd.DataFrame(pnl_data, columns=['time', 'value', 'profit_pct'])
                
                # 为原始 DataFrame 中的每个时间点分配 PNL 值
                last_pnl = 1000
                last_pct = 0
                
                for i, row in df.iterrows():
                    current_time = row['datetime']
                    # 找到当前时间之前的最后一个 PNL 值
                    prev_pnl = pnl_df[pnl_df['time'] <= current_time]
                    
                    if not prev_pnl.empty:
                        last_pnl = prev_pnl.iloc[-1]['value']
                        last_pct = (last_pnl - 1000) / 1000 * 100
                    
                    df.at[i, 'cumulative_pnl'] = last_pnl
                    df.at[i, 'pnl_percentage'] = last_pct
            
            # 添加统计信息到图表中
            stats_text = f"<b>交易统计</b><br>"
            stats_text += f"交易次数: <b>{total_trades}</b><br>"
            stats_text += f"胜率: <b>{win_rate:.2f}%</b><br>"
            stats_text += f"总收益率: <b>{total_return:.2f}%</b><br>"
            stats_text += f"平均收益率: <b>{avg_return:.2f}%</b>"
            if pnl_data:
                stats_text += f"<br>最终账户价值: <b>{last_pnl:.2f}</b>"

            # 添加注释
            fig.add_annotation(
                xref="paper", yref="paper",
                x=0.01, y=0.01,
                text=stats_text,
                showarrow=False,
                font=dict(size=12, color='white'),
                align="left",
                bgcolor="rgba(30, 30, 30, 0.8)",
                bordercolor="rgba(100, 100, 100, 0.5)",
                borderwidth=2,
                borderpad=10,
                row=1, col=1
            )  
    # 添加成交量图
    fig.add_trace(
        go.Bar(
            x=df['datetime'],
            y=df['volume'],
            name='Volume',
            marker=dict(
                color=np.where(df['close'] >= df['open'], '#00FFEA', '#FF5252'),  # 根据K线涨跌设置颜色
                opacity=0.7
            )
        ),
        row=2, col=1
    )
    
    # 添加累计 PNL 曲线
    if 'cumulative_pnl' in df.columns and 'pnl_percentage' in df.columns:
        # 创建新的子图用于显示 PNL
        fig.add_trace(
            go.Scatter(
                x=df['datetime'],
                y=df['pnl_percentage'],
                name='累计收益率 (%)',
                line=dict(color='#FFD700', width=2),  # 金色
                hovertemplate='%{x}<br>收益率: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )
        
        # 添加水平线表示盈亏平衡点
        fig.add_shape(
            type="line",
            x0=df['datetime'].iloc[0],
            y0=0,
            x1=df['datetime'].iloc[-1],
            y1=0,
            line=dict(color="white", width=1, dash="dash"),
            row=3, col=1
        )  
        
    # 添加叠加在价格图上的指标
    colors = ['#2962FF', '#FFEB3B', '#00BCD4', '#4CAF50', '#FF5722', '#E040FB']
    for i, ind in enumerate(overlay_indicators):
        color_idx = i % len(colors)
        fig.add_trace(
            go.Scatter(
                x=df['datetime'],
                y=df[ind],
                mode='lines',
                name=ind,
                line=dict(width=1.5, color=colors[color_idx]),
                opacity=0.8
            ),
            row=1, col=1
        )
    
    # 添加需要单独显示的指标
    for i, ind in enumerate(separate_indicators):
        fig.add_trace(
            go.Scatter(
                x=df['datetime'],
                y=df[ind],
                mode='lines',
                name=ind,
                line=dict(width=1.5)
            ),
            row=i+3, col=1
        )
    
    # 根据时间周期和聚合周期动态生成时间范围选择器按钮
    range_buttons = []
    
    # 根据不同的时间周期生成适合的按钮
    if timeframe == 'minute':
        # 分钟级数据
        if aggregate <= 5:  # 1-5分钟 K线
            range_buttons = [
                dict(count=1, label="1小时", step="hour", stepmode="backward"),
                dict(count=6, label="6小时", step="hour", stepmode="backward"),
                dict(count=12, label="12小时", step="hour", stepmode="backward"),
                dict(count=1, label="1天", step="day", stepmode="backward"),
                dict(count=3, label="3天", step="day", stepmode="backward"),
                dict(count=7, label="1周", step="day", stepmode="backward"),
                dict(step="all", label="全部")
            ]
        elif aggregate <= 15:  # 5-15分钟 K线
            range_buttons = [
                dict(count=6, label="6小时", step="hour", stepmode="backward"),
                dict(count=12, label="12小时", step="hour", stepmode="backward"),
                dict(count=1, label="1天", step="day", stepmode="backward"),
                dict(count=3, label="3天", step="day", stepmode="backward"),
                dict(count=7, label="1周", step="day", stepmode="backward"),
                dict(count=14, label="2周", step="day", stepmode="backward"),
                dict(step="all", label="全部")
            ]
        else:  # 15分钟以上
            range_buttons = [
                dict(count=1, label="1天", step="day", stepmode="backward"),
                dict(count=3, label="3天", step="day", stepmode="backward"),
                dict(count=7, label="1周", step="day", stepmode="backward"),
                dict(count=14, label="2周", step="day", stepmode="backward"),
                dict(count=1, label="1月", step="month", stepmode="backward"),
                dict(step="all", label="全部")
            ]
    elif timeframe == 'hour':
        # 小时级数据
        if aggregate <= 2:  # 1-2小时 K线
            range_buttons = [
                dict(count=1, label="1天", step="day", stepmode="backward"),
                dict(count=3, label="3天", step="day", stepmode="backward"),
                dict(count=7, label="1周", step="day", stepmode="backward"),
                dict(count=14, label="2周", step="day", stepmode="backward"),
                dict(count=1, label="1月", step="month", stepmode="backward"),
                dict(step="all", label="全部")
            ]
        else:  # 3小时以上 K线
            range_buttons = [
                dict(count=3, label="3天", step="day", stepmode="backward"),
                dict(count=7, label="1周", step="day", stepmode="backward"),
                dict(count=14, label="2周", step="day", stepmode="backward"),
                dict(count=1, label="1月", step="month", stepmode="backward"),
                dict(count=3, label="3月", step="month", stepmode="backward"),
                dict(step="all", label="全部")
            ]
    else:  # 日级数据
        range_buttons = [
            dict(count=7, label="7天", step="day", stepmode="backward"),
            dict(count=14, label="14天", step="day", stepmode="backward"),
            dict(count=1, label="1月", step="month", stepmode="backward"),
            dict(count=3, label="3月", step="month", stepmode="backward"),
            dict(count=6, label="6月", step="month", stepmode="backward"),
            dict(count=1, label="1年", step="year", stepmode="backward"),
            dict(step="all", label="全部")
        ]
    
    # 更新布局
    fig.update_layout(
        title=dict(
            text=title if title else "价格图表",
            x=0.5,  # 居中标题
            font=dict(size=20, color="#ffffff")
        ),
        height=800,  # 增加图表高度
        margin=dict(l=50, r=50, t=50, b=50),  # 减小顶部边距
        paper_bgcolor='rgb(15, 15, 15)',  # 暗色图表背景
        plot_bgcolor='rgb(15, 15, 15)',   # 暗色绘图区背景
        font=dict(family="Arial, sans-serif", size=12, color="#cccccc"),  # 亮色字体
        hovermode="x unified",  # 统一悬停模式
        xaxis=dict(
            rangeselector=dict(
                buttons=range_buttons,
                bgcolor="rgba(50, 50, 50, 0.8)",
                activecolor="rgba(0, 123, 255, 0.7)",
                font=dict(color="#cccccc", size=10),
                x=0.01,  # 位置调整到左侧
                y=0.99,
                xanchor='left',
                yanchor='top'
            ),
            rangeslider=dict(visible=False),  # 隐藏范围滑块以节省空间
            tickformat='%Y-%m-%d %H:%M' if timeframe in ['minute', 'hour'] else '%Y-%m-%d'  # 根据时间周期调整日期格式
        )
    )
    
    # 更新所有子图的网格线和背景 - 暗色主题
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(80,80,80,0.3)',  # 降低网格线不透明度
        zeroline=False,
        showline=True,
        linewidth=1,
        linecolor='rgba(80,80,80,0.8)',  # 暗色轴线
        tickformat='%b %Y',  # 简化日期格式为 'Jan 2025'
        nticks=10  # 减少刻度数量
    )

    # 检测价格范围，动态调整小数位数
    min_price = df['low'].min()
    if min_price < 0.0001:
        decimal_places = 10  # 非常小的单位
    elif min_price < 0.01:
        decimal_places = 8   # 很小的单位
    elif min_price < 1:
        decimal_places = 6   # 小单位
    else:
        decimal_places = 4   # 正常单位
    
    # 根据币种单位大小动态调整格式
    price_format = f'.{decimal_places}f'
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(80,80,80,0.3)',  # 降低网格线不透明度
        zeroline=False,
        showline=True,
        linewidth=1,
        linecolor='rgba(80,80,80,0.8)',  # 暗色轴线
        tickformat=price_format,  # 动态调整小数位数
        nticks=8  # 减少刻度数量
    )
    
    # 更新 Y 轴标题
    fig.update_yaxes(title_text="Price", row=1, col=1, title_font=dict(size=10))
    fig.update_yaxes(title_text="Volume", row=2, col=1, title_font=dict(size=10))
    for i, ind in enumerate(separate_indicators):
        fig.update_yaxes(title_text=ind, row=i+3, col=1, title_font=dict(size=10))

    # 更新 X 轴
    fig.update_xaxes(title_text="Date", row=n_subplots, col=1, title_font=dict(size=10))
    
    # 保存图表
    if save_path:
        if not save_path.endswith('.html'):
            save_path += '.html'
        fig.write_html(save_path)
        print(f"交互式图表已保存到 {save_path}")
    
    # 将图表导出为JSON
    if save_json:
        if not save_json.endswith('.json'):
            save_json += '.json'
        
        # 将图表转换为JSON
        fig_json = fig.to_json()
        
        # 保存JSON文件
        with open(save_json, 'w', encoding='utf-8') as f:
            f.write(fig_json)
        
        print(f"图表JSON已保存到 {save_json}")
    
    # 显示图表
    if show:
        fig.show()
    
    return fig
