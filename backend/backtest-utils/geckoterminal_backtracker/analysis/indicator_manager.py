"""
指标管理模块
用于管理和列出已保存的指标
"""

import os
import re
import json
import importlib.util
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

def list_indicators(directory: str = 'indicators', detail: bool = False, filter_keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出所有已保存的指标
    
    参数:
        directory (str): 指标代码目录
        detail (bool): 是否显示详细信息
        filter_keyword (str, optional): 按关键词过滤
        
    返回:
        List[Dict[str, Any]]: 指标信息列表
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return []
    
    indicators = []
    
    # 遍历目录中的所有 Python 文件
    for filename in os.listdir(directory):
        if filename.endswith('.py'):
            file_path = os.path.join(directory, filename)
            
            # 提取指标名称
            indicator_name = filename[:-3].replace('_', ' ').title()
            
            # 读取文件内容
            with open(file_path, 'r') as f:
                content = f.read()
            
            # 提取描述和生成时间
            description = ""
            created_at = ""
            
            desc_match = re.search(r'描述:\s*(.*?)(?=\n\n)', content, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
            
            time_match = re.search(r'生成时间:\s*(.*?)(?=\n)', content)
            if time_match:
                created_at = time_match.group(1).strip()
            
            # 应用过滤
            if filter_keyword and filter_keyword.lower() not in indicator_name.lower() and filter_keyword.lower() not in description.lower():
                continue
            
            indicator_info = {
                'name': indicator_name,
                'file': filename,
                'path': file_path,
                'created_at': created_at
            }
            
            if detail:
                # 提取函数名
                func_match = re.search(r'def\s+([a-zA-Z0-9_]+)\s*\(', content)
                function_name = func_match.group(1) if func_match else ""
                
                # 提取代码
                code_start = content.find('def ')
                if code_start != -1:
                    code = content[code_start:]
                else:
                    code = ""
                
                indicator_info.update({
                    'description': description,
                    'function_name': function_name,
                    'code': code if detail else ""
                })
            else:
                indicator_info['description'] = description[:100] + '...' if len(description) > 100 else description
            
            indicators.append(indicator_info)
    
    # 按创建时间排序，最新的在前面
    indicators.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return indicators

def load_indicator(file_path: str) -> Optional[callable]:
    """
    加载指标函数
    
    参数:
        file_path (str): 指标文件路径
        
    返回:
        callable: 指标函数
    """
    if not os.path.exists(file_path):
        return None
    
    # 提取模块名
    module_name = os.path.basename(file_path)[:-3]
    
    # 加载模块
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 查找函数
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if callable(attr) and (attr_name.startswith('calculate_') or 'def ' + attr_name in open(file_path).read()):
            return attr
    
    return None

def find_indicator_file(indicator_name: str, directory: str = 'indicators') -> Optional[str]:
    """
    根据指标名称查找指标文件
    
    参数:
        indicator_name (str): 指标名称或文件名
        directory (str): 指标代码目录
        
    返回:
        str: 指标文件路径
    """
    if not os.path.exists(directory):
        return None
    
    # 如果提供的是文件名
    if indicator_name.endswith('.py'):
        file_path = os.path.join(directory, indicator_name)
        if os.path.exists(file_path):
            return file_path
    
    # 如果提供的是指标名称
    # 尝试直接匹配文件名
    file_name = indicator_name.lower().replace(' ', '_') + '.py'
    file_path = os.path.join(directory, file_name)
    if os.path.exists(file_path):
        return file_path
    
    # 如果没有直接匹配，搜索所有指标文件
    indicators = list_indicators(directory)
    
    # 按名称相似度排序
    matching_indicators = []
    for ind in indicators:
        if indicator_name.lower() in ind['name'].lower() or indicator_name.lower() in ind.get('description', '').lower():
            matching_indicators.append(ind)
    
    if matching_indicators:
        # 返回最匹配的指标
        return matching_indicators[0]['path']
    
    return None

def use_indicator(df: pd.DataFrame, indicator_name: str, directory: str = 'indicators') -> tuple:
    """
    使用已保存的指标
    
    参数:
        df (pandas.DataFrame): 输入数据
        indicator_name (str): 指标名称或文件名
        directory (str): 指标代码目录
        
    返回:
        tuple: (DataFrame, 指标信息)
    """
    # 查找指标文件
    file_path = find_indicator_file(indicator_name, directory)
    if not file_path:
        raise ValueError(f"找不到指标: {indicator_name}")
    
    # 加载指标函数
    indicator_func = load_indicator(file_path)
    if not indicator_func:
        raise ValueError(f"无法加载指标函数: {file_path}")
    
    # 提取指标信息
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 提取指标名称和描述
    name = os.path.basename(file_path)[:-3].replace('_', ' ').title()
    description = ""
    desc_match = re.search(r'描述:\s*(.*?)(?=\n\n)', content, re.DOTALL)
    if desc_match:
        description = desc_match.group(1).strip()
    
    # 应用指标
    result_df = indicator_func(df.copy())
    
    # 识别新增的列
    new_columns = [col for col in result_df.columns if col not in df.columns]
    
    indicator_info = {
        'name': name,
        'description': description,
        'file_path': file_path,
        'new_columns': new_columns
    }
    
    return result_df, indicator_info

def print_indicators_table(indicators: List[Dict[str, Any]]) -> None:
    """
    打印指标表格
    
    参数:
        indicators (List[Dict[str, Any]]): 指标信息列表
    """
    if not indicators:
        print("没有找到指标。使用 'ai-indicator' 命令创建指标。")
        return
    
    # 计算列宽
    name_width = max(len(ind['name']) for ind in indicators) + 2
    date_width = max(len(ind.get('created_at', '')) for ind in indicators) + 2
    desc_width = 60
    
    # 打印表头
    header = f"{'名称':<{name_width}} | {'创建时间':<{date_width}} | {'描述':<{desc_width}}"
    separator = "-" * (name_width + date_width + desc_width + 6)
    
    print(separator)
    print(header)
    print(separator)
    
    # 打印指标信息
    for ind in indicators:
        desc = ind.get('description', '')
        if len(desc) > desc_width:
            desc = desc[:desc_width-3] + '...'
        
        print(f"{ind['name']:<{name_width}} | {ind.get('created_at', ''):<{date_width}} | {desc:<{desc_width}}")
    
    print(separator)
    print(f"共找到 {len(indicators)} 个指标")
