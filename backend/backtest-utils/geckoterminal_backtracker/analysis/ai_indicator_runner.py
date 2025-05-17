"""
AI 指标生成器运行模块
用于加载数据并应用 AI 生成的指标
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from ..storage.csv_storage import CSVStorage
from ..storage.sqlite_storage import SQLiteStorage
from .analyzer import OHLCAnalyzer

def generate_ai_indicator(args):
    """
    使用自然语言生成并应用技术指标
    
    参数:
        args: 命令行参数
    """
    # 创建必要的目录
    os.makedirs(args.data_dir, exist_ok=True)
    if args.save:
        os.makedirs(args.output_dir, exist_ok=True)
    if args.save_chart:
        os.makedirs(args.chart_dir, exist_ok=True)
    
    # 加载数据
    print(f"正在加载 {args.network} 网络上 {args.pool} 池子的数据...")
    
    # 根据存储类型选择存储对象
    if args.storage == 'csv':
        storage = CSVStorage(args.data_dir)
    else:
        storage = SQLiteStorage(args.data_dir)
    
    # 构建文件名
    timeframe_str = f"{args.timeframe}_{args.aggregate}" if args.aggregate > 1 else args.timeframe
    
    # 尝试加载数据
    try:
        df = storage.load_ohlc_data(args.network, args.pool, timeframe_str)
        if df.empty:
            print(f"未找到数据，请先使用 fetch 命令获取数据")
            return
    except Exception as e:
        print(f"加载数据时出错: {str(e)}")
        print(f"请先使用 fetch 命令获取数据")
        return
    
    print(f"成功加载数据，共 {len(df)} 条记录")
    
    # 创建分析器
    try:
        analyzer = OHLCAnalyzer(df, api_key=args.api_key)
    except ValueError as e:
        print(f"错误: {str(e)}")
        return
    
    # 打印数据摘要
    stats = analyzer.get_summary_stats()
    print("\n数据摘要:")
    print(f"开始日期: {stats['start_date']}")
    print(f"结束日期: {stats['end_date']}")
    print(f"数据点数: {stats['data_points']}")
    print(f"价格变化: {stats['price_change']:.6f} ({stats['price_change_pct']:.2f}%)")
    print(f"最高价: {stats['high_max']:.6f} (日期: {stats['high_date']})")
    print(f"最低价: {stats['low_min']:.6f} (日期: {stats['low_date']})")
    print(f"总成交量: {stats['volume_total']:.2f}")
    print(f"平均波动率: {stats['volatility_avg']:.2f}%")
    
    # 生成并应用 AI 指标
    print(f"\n正在使用自然语言描述生成指标: \"{args.description}\"")
    print(f"使用模型: {args.model}")
    
    try:
        # 生成并应用指标
        result_df = analyzer.create_ai_indicator(args.description, args.model)
        
        # 保存指标代码
        if args.save:
            file_path = analyzer.save_ai_indicator(args.description, args.name, args.output_dir)
            print(f"\n指标代码已保存到: {file_path}")
        
        # 识别新增的列
        new_columns = [col for col in result_df.columns if col not in df.columns]
        
        if not new_columns:
            print("\n警告: 未检测到新增的指标列，请检查生成的指标代码")
        else:
            print(f"\n成功生成指标，新增列: {', '.join(new_columns)}")
            
            # 显示新列的前几行数据
            print("\n指标数据预览:")
            preview_df = result_df[['datetime'] + new_columns].tail(5)
            print(preview_df.to_string(index=False))
            
            # 绘制图表
            if args.plot or args.save_chart:
                # 创建图表文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                chart_filename = f"{args.name.lower().replace(' ', '_')}_{timestamp}.png"
                chart_path = os.path.join(args.chart_dir, chart_filename) if args.save_chart else None
                
                # 绘制图表
                analyzer.plot_with_indicators(new_columns, 
                                             title=f"{args.name} - {args.network.upper()} {args.pool}",
                                             save_path=chart_path)
                
                if args.save_chart:
                    print(f"\n图表已保存到: {chart_path}")
        
        # 保存带有指标的数据
        if args.storage == 'csv':
            # 构建输出文件名
            output_filename = f"{args.network}_{args.pool}_{timeframe_str}_with_{args.name.lower().replace(' ', '_')}.csv"
            output_path = os.path.join(args.data_dir, output_filename)
            
            # 保存到 CSV
            result_df.to_csv(output_path, index=False)
            print(f"\n带有指标的数据已保存到: {output_path}")
        else:
            # 保存到 SQLite
            table_name = f"{args.network}_{args.pool}_{timeframe_str}_with_{args.name.lower().replace(' ', '_')}"
            storage.save_dataframe(result_df, table_name)
            print(f"\n带有指标的数据已保存到 SQLite 表: {table_name}")
    
    except Exception as e:
        print(f"\n生成指标时出错: {str(e)}")
        import traceback
        traceback.print_exc()
