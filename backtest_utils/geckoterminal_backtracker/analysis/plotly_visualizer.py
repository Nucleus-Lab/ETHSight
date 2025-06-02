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
                        save_path: Optional[str] = None, show: bool = False, 
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
    
    # ============================================================================
    # 1. DATA VALIDATION & PREPROCESSING
    # ============================================================================
    
    # 验证指标是否存在
    missing_indicators = [ind for ind in indicators if ind not in df.columns]
    if missing_indicators:
        raise ValueError(f"以下指标不存在于数据中: {', '.join(missing_indicators)}")
    
    # 检查必要的列是否存在
    required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"缺少K线图所需的列: {', '.join(missing_columns)}")
    
    # 计算涨跌幅
    df.loc[:, 'change_pct'] = ((df['close'] - df['open']) / df['open'] * 100).round(2)
    
    # ============================================================================
    # 2. INDICATOR CLASSIFICATION
    # ============================================================================
    
    # 分类指标
    signal_indicators = []
    overlay_indicators = []  # 可以叠加在价格图上的指标（如移动平均线）
    
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
            
        # 跳过所有MACD相关指标，避免它们被添加到价格图上
        if 'macd' in ind.lower() or 'signal_line' in ind.lower():
            print(f"跳过MACD指标: {ind}")
            continue
            
        # 判断是否可以叠加在价格图上（移动平均线、趋势线等）
        if 'ma' in ind.lower() or 'ema' in ind.lower() or 'sma' in ind.lower() or 'wma' in ind.lower() or \
             'avg' in ind.lower() or 'mean' in ind.lower() or 'support' in ind.lower() or 'resistance' in ind.lower() or \
             'trend' in ind.lower() or 'line' in ind.lower() or 'band' in ind.lower() or \
             '均线' in ind or '支撑' in ind or '压力' in ind or '趋势' in ind:
            overlay_indicators.append(ind)
        
    # 打印分类结果
    print(f"\n识别到的信号指标: {signal_indicators}")
    print(f"识别到的叠加指标: {overlay_indicators}")
    
    # ============================================================================
    # 3. CREATE SUBPLOT LAYOUT
    # ============================================================================
    
    # 定义子图结构：价格图 + MACD图 + 累计PnL图
    n_subplots = 3
    subplot_titles = ['Price & Signals', 'MACD', 'Cumulative PnL (%)']
    row_heights = [0.6, 0.25, 0.15]  # 价格图占60%，MACD占25%，PnL占15%

    # 创建子图布局
    fig = make_subplots(
        rows=n_subplots, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=subplot_titles,
        row_heights=row_heights,
        specs=[[{"secondary_y": False}],      # 第1行：价格图
               [{"secondary_y": False}],      # 第2行：MACD图
               [{"secondary_y": False}]]      # 第3行：PnL图
    )
    
    # ============================================================================
    # 4. CONFIGURE CHART TITLE & LAYOUT
    # ============================================================================
    
    # 设置图表标题
    if title:
        chart_title = title
    else:
        # 尝试从数据中提取代币信息
        if 'base_token_symbol' in df.columns and 'quote_token_symbol' in df.columns:
            base = df['base_token_symbol'].iloc[0] if not pd.isna(df['base_token_symbol'].iloc[0]) else 'Base'
            quote = df['quote_token_symbol'].iloc[0] if not pd.isna(df['quote_token_symbol'].iloc[0]) else 'Quote'
            chart_title = f"{base}/{quote} Strategy Analysis"
        else:
            chart_title = "Strategy Analysis"

    # 配置响应式布局
    fig.update_layout(
        title={
            'text': chart_title,
            'x': 0.5,  # 居中
            'y': 0.98,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18)
        },
        height=None,  # 让前端控制高度
        margin=dict(l=10, r=0, t=80, b=20),  # 增加顶部边距为图例留空间
        paper_bgcolor='rgb(15, 15, 15)',  # 深色背景
        plot_bgcolor='rgb(15, 15, 15)',   # 深色绘图区
        font=dict(family="Arial, sans-serif", size=10, color="#cccccc"),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",  # 水平图例
            yanchor="top",
            y=1.01,  # 移动到更高位置，增加与图表的距离
            xanchor="center",  # 居中对齐
            x=0.5,
            font=dict(size=9),
            bgcolor="rgba(15, 15, 15, 0.8)",  # 半透明背景
            bordercolor="rgba(100, 100, 100, 0.3)",  # 淡边框
            borderwidth=0.5
        ),
        # Enable autosize to work with React's responsive config
        autosize=True
    )
    
    print(f"=== 布局设置完成 ===")
    print(f"设置的边距: l=10, r=0, t=80, b=20")
    print(f"Autosize: True (配合React响应式)")
    print(f"Width: None (让前端控制)")
    
    # ============================================================================
    # 5. ROW 1: PRICE CHART (CANDLESTICKS + SIGNALS + OVERLAYS)
    # ============================================================================
    
    print("\n=== 添加价格图表 ===")
    
    # 5.1 添加K线图
    fig.add_trace(
        go.Candlestick(
            x=df['datetime'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing=dict(line=dict(color='#00FFEA', width=1), fillcolor='#00FFEA'),  # 青色上涨
            decreasing=dict(line=dict(color='#FF5252', width=1), fillcolor='#FF5252'),  # 红色下跌
            line=dict(width=1),
            whiskerwidth=0.8,
        ),
        row=1, col=1
    )
    
    # 5.2 添加买卖信号标记
    for signal_ind in signal_indicators:
        if signal_ind in ['buy_signal', 'sell_signal']:
            signals = df[df[signal_ind] == 1].copy()
            if not signals.empty:
                price_range = df['high'].max() - df['low'].min()
                offset = price_range * 0.02
                
                if 'buy' in signal_ind:
                    y_pos = signals['high'] + offset
                    color = '#00FFEA'
                    text = ['B'] * len(signals)
                    name = 'Buy Signal'
                    print(f"添加买入信号: {len(signals)} 个点")
                else:
                    y_pos = signals['low'] - offset
                    color = '#FF5252'
                    text = ['S'] * len(signals)
                    name = 'Sell Signal'
                    print(f"添加卖出信号: {len(signals)} 个点")
                
                fig.add_trace(
                    go.Scatter(
                        x=signals['datetime'],
                        y=y_pos,
                        mode='markers+text',
                        name=name,
                        text=text,
                        textposition='middle center',
                        marker=dict(
                            symbol='circle',
                            size=12,
                            color=color,
                            line=dict(width=1, color=color),
                            opacity=0.9
                        ),
                        textfont=dict(color='white', size=8, family='Arial Black'),
                        showlegend=False  # 不在图例中显示信号点
                    ),
                    row=1, col=1
                )
    
    # 5.3 添加叠加指标（移动平均线等）
    if overlay_indicators:
        print(f"添加叠加指标: {overlay_indicators}")
        colors = ['#2962FF', '#FFEB3B', '#00BCD4', '#4CAF50']
        for i, ind in enumerate(overlay_indicators):
            color_idx = i % len(colors)
            fig.add_trace(
                go.Scatter(
                    x=df['datetime'],
                    y=df[ind],
                    mode='lines',
                    name=ind,
                    line=dict(width=1, color=colors[color_idx]),
                    opacity=0.8
                ),
                row=1, col=1
            )
    
    # ============================================================================
    # 6. ROW 2: MACD CHART
    # ============================================================================
    
    print("\n=== 添加MACD图表 ===")
    
    # 6.1 添加MACD线
    fig.add_trace(
        go.Scatter(
            x=df['datetime'],
            y=df['macd'],
            name='MACD',
            line=dict(color='#00BFFF', width=2),  # 天蓝色线条
            showlegend=False
        ),
        row=2, col=1
    )
    
    # 6.2 添加信号线
    fig.add_trace(
        go.Scatter(
            x=df['datetime'],
            y=df['signal_line'],
            name='Signal Line',
            line=dict(color='#FFA500', width=2),  # 橙色线条
            showlegend=False
        ),
        row=2, col=1
    )
    
    # 6.3 添加MACD柱状图
    fig.add_trace(
        go.Bar(
            x=df['datetime'],
            y=df['macd_histogram'],
            name='MACD Histogram',
            marker=dict(
                color=np.where(df['macd_histogram'] >= 0, '#4CAF50', '#FF5252'),  # 绿色上涨，红色下跌
                opacity=0.6
            ),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # 6.4 添加零线
    fig.add_shape(
        type="line",
        x0=df['datetime'].iloc[0],
        y0=0,
        x1=df['datetime'].iloc[-1],
        y1=0,
        line=dict(color="white", width=1, dash="dash"),
        row=2, col=1
    )
    
    # ============================================================================
    # 7. ROW 3: CUMULATIVE PNL CHART
    # ============================================================================
    
    print("\n=== 添加累计PnL图表 ===")
    
    # 7.1 计算累计PnL
    df['cumulative_pnl'] = 0.0
    df['pnl_percentage'] = 0.0
    
    # 简化PNL计算逻辑
    if 'buy_signal' in df.columns and 'sell_signal' in df.columns:
        buy_signals = df[df['buy_signal'] == 1]
        sell_signals = df[df['sell_signal'] == 1]
        
        if not buy_signals.empty and not sell_signals.empty:
            print(f"计算PnL: {len(buy_signals)} 个买入信号, {len(sell_signals)} 个卖出信号")
            
            # 模拟交易计算累计收益
            initial_value = 1000
            current_value = initial_value
            in_position = False
            entry_price = 0
            
            for idx, row in df.iterrows():
                if row['buy_signal'] == 1 and not in_position:
                    entry_price = row['close']
                    in_position = True
                elif row['sell_signal'] == 1 and in_position:
                    profit_pct = (row['close'] - entry_price) / entry_price
                    current_value *= (1 + profit_pct)
                    in_position = False
                
                df.at[idx, 'cumulative_pnl'] = current_value
                df.at[idx, 'pnl_percentage'] = (current_value - initial_value) / initial_value * 100
    
    # 7.2 添加累计PnL曲线
    fig.add_trace(
        go.Scatter(
            x=df['datetime'],
            y=df['pnl_percentage'],
            name='Cumulative PnL (%)',
            line=dict(color='#FFD700', width=2),  # 金色线条
            fill='tonexty' if df['pnl_percentage'].iloc[-1] >= 0 else None,
            fillcolor='rgba(255, 215, 0, 0.1)',
            showlegend=False
        ),
        row=3, col=1
    )
    
    # 7.3 添加盈亏平衡线（零线）
    fig.add_shape(
        type="line",
        x0=df['datetime'].iloc[0],
        y0=0,
        x1=df['datetime'].iloc[-1],
        y1=0,
        line=dict(color="white", width=1, dash="dash"),
        row=3, col=1
    )
    
    # ============================================================================
    # 8. CONFIGURE AXES & STYLING
    # ============================================================================
    
    print("\n=== 配置坐标轴样式 ===")
    
    # 8.1 更新X轴样式
    fig.update_xaxes(
        showgrid=True,
        gridwidth=0.5,
        gridcolor='rgba(80,80,80,0.2)',
        zeroline=False,
        showline=True,
        linewidth=0.5,
        linecolor='rgba(80,80,80,0.5)',
        tickfont=dict(size=9)
    )
    
    # 8.2 更新Y轴样式
    fig.update_yaxes(
        showgrid=True,
        gridwidth=0.5,
        gridcolor='rgba(80,80,80,0.2)',
        zeroline=False,
        showline=True,
        linewidth=0.5,
        linecolor='rgba(80,80,80,0.5)',
        tickfont=dict(size=9)
    )
    
    # 8.3 设置各子图的Y轴标题
    fig.update_yaxes(title=dict(text="Price", font=dict(size=10)), row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(title=dict(text="PnL %", font=dict(size=10)), row=3, col=1)
    
    # 8.4 设置X轴标题（只在最后一行显示）
    fig.update_xaxes(title=dict(text="Time", font=dict(size=10)), row=3, col=1)
    
    # 8.5 移除范围选择器以节省空间
    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(visible=False),
            tickformat='%m/%d' if timeframe in ['minute', 'hour'] else '%m/%d'
        )
    )
    
    # ============================================================================
    # 9. SAVE & DISPLAY
    # ============================================================================
    
    print("\n=== 保存和显示图表 ===")
    
    # 9.1 保存HTML文件
    if save_path:
        if not save_path.endswith('.html'):
            save_path += '.html'
        fig.write_html(save_path)
        print(f"交互式图表已保存到 {save_path}")
    
    # 9.2 保存JSON文件
    if save_json:
        if not save_json.endswith('.json'):
            save_json += '.json'
        
        fig_json = fig.to_json()
        with open(save_json, 'w', encoding='utf-8') as f:
            f.write(fig_json)
        
        print(f"图表JSON已保存到 {save_json}")
    
    # 9.3 显示图表
    if show:
        fig.show()
    
    print("=== 图表生成完成 ===\n")
    return fig
