"""
AI 指标生成器运行模块
用于加载数据并应用 AI 生成的指标
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# 导入 Plotly 可视化模块
from .plotly_visualizer import plot_with_indicators

from ..storage.csv_storage import CSVStorage
from ..storage.sqlite_storage import SQLiteStorage
from .analyzer import OHLCAnalyzer
from .ai_indicator_generator import AIIndicatorGenerator

def generate_ai_indicator(args):
    """
    使用自然语言生成并应用技术指标
    
    参数:
        args: 命令行参数
    """
    # 加载.env文件中的环境变量
    load_dotenv()
    # 创建必要的目录
    if args.save:
        os.makedirs(args.output_dir, exist_ok=True)
    
    # 创建指标生成器
    try:
        # 优先使用命令行参数中的API密钥，如果没有则使用环境变量中的密钥
        api_key = args.api_key if hasattr(args, 'api_key') and args.api_key else os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("错误: 未提供OpenAI API密钥。请在.env文件中设置OPENAI_API_KEY或通过--api-key参数提供")
            return
            
        # 创建指标生成器
        indicator_generator = AIIndicatorGenerator(api_key)
    except ValueError as e:
        print(f"错误: {str(e)}")
        return
    
    # 生成 AI 指标
    print(f"\n正在使用自然语言描述生成指标: \"{args.description}\"")
    print(f"使用模型: {args.model}")
    
    try:
        # 生成指标代码
        indicator_code = indicator_generator.generate_indicator_code(args.description, args.model)
        
        # 保存指标代码
        if args.save:
            # 创建输出目录
            os.makedirs(args.output_dir, exist_ok=True)
            
            # 构建文件路径
            file_name = f"{args.name.lower().replace(' ', '_')}.py"
            file_path = os.path.join(args.output_dir, file_name)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(indicator_code)
                
            print(f"\n指标代码已保存到: {file_path}")
            print("\n如需查看图表，请使用以下命令:")
            print(f"python main.py use-indicator --network <网络> --pool <池子地址> --indicator {args.name} --plot")
        else:
            # 如果不保存，直接显示代码
            print("\n生成的指标代码:\n")
            print(indicator_code)
            print("\n使用 --save 参数可保存指标代码到文件")
        
        # 如果用户指定了绘图参数，显示提示
        if hasattr(args, 'plot') and (args.plot or args.save_chart):
            print("\n注意: --plot 和 --save-chart 参数已被忽略。请使用 use-indicator 命令查看图表。")
    
    except Exception as e:
        print(f"\n生成指标时出错: {str(e)}")
        import traceback
        traceback.print_exc()
