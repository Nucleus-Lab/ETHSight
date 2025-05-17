"""
AI 驱动的指标生成器
使用 OpenAI API 将自然语言描述转换为技术指标代码
"""

import os
import json
import pandas as pd
import numpy as np
import requests
from typing import Dict, Any, List, Optional, Union

class AIIndicatorGenerator:
    """
    AI 驱动的指标生成器
    使用 OpenAI API 将自然语言描述转换为技术指标代码
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 AI 指标生成器
        
        参数:
            api_key (str, optional): OpenAI API 密钥，如果不提供，将尝试从环境变量 OPENAI_API_KEY 获取
        """
        # 优先使用传入的 API 密钥，如果没有则从环境变量获取
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("需要提供 OpenAI API 密钥，可以通过参数传入或设置环境变量 OPENAI_API_KEY")
        
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def generate_indicator_code(self, description: str, model: str = "gpt-4.1") -> str:
        """
        根据自然语言描述生成指标代码
        
        参数:
            description (str): 指标的自然语言描述
            model (str): 要使用的 OpenAI 模型
            
        返回:
            str: 生成的 Python 代码
        """
        prompt = self._create_prompt(description)
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的金融技术指标开发专家，精通 Python 和 pandas。你的任务是将用户的自然语言描述转换为可执行的 Python 代码，用于计算金融技术指标。代码应该接受一个包含 OHLC (Open, High, Low, Close) 和 Volume 列的 pandas DataFrame，并返回添加了新指标列的 DataFrame。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            code = result['choices'][0]['message']['content']
            
            # 提取代码块
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
            
            return code
        
        except Exception as e:
            raise Exception(f"调用 OpenAI API 时出错: {str(e)}")
    
    def _create_prompt(self, description: str) -> str:
        """
        创建发送给 OpenAI API 的提示
        
        参数:
            description (str): 指标的自然语言描述
            
        返回:
            str: 格式化的提示
        """
        return f"""
请根据以下描述创建一个金融技术指标的 Python 函数:

描述: {description}

要求:
1. 函数应该接受一个 pandas DataFrame 作为输入，该 DataFrame 包含timestamp,open,high,low,close,volume,datetime,base_token_address,base_token_name,base_token_symbol,quote_token_address,quote_token_name,quote_token_symbol列
2. 函数应该返回原始 DataFrame，但添加了新的指标列
3. 使用 pandas 和 numpy 进行计算
4. 函数名应该反映指标的用途
5. 包含详细的文档字符串，解释指标的计算方法和用途
6. 代码应该高效且易于理解
7. 只返回 Python 代码，不要包含任何其他解释

示例函数格式:
```python
def calculate_indicator(df):
    \"\"\"
    计算某某指标
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame
        
    返回:
        pandas.DataFrame: 添加了指标列的 DataFrame
    \"\"\"
    # 计算逻辑
    df['indicator_name'] = ...
    
    return df
```

请只返回 Python 代码，不要包含任何其他解释。
"""
    
    def apply_indicator(self, df: pd.DataFrame, description: str, model: str = "gpt-4.1") -> pd.DataFrame:
        """
        生成并应用指标到 DataFrame
        
        参数:
            df (pandas.DataFrame): 输入数据
            description (str): 指标的自然语言描述
            model (str): 要使用的 OpenAI 模型
            
        返回:
            pandas.DataFrame: 添加了指标的 DataFrame
        """
        code = self.generate_indicator_code(description, model)
        
        # 提取函数名
        function_name = None
        for line in code.split('\n'):
            if line.startswith('def '):
                function_name = line.split('def ')[1].split('(')[0].strip()
                break
        
        if not function_name:
            raise ValueError("无法从生成的代码中提取函数名")
        
        # 创建临时模块并执行代码
        local_vars = {}
        exec(code, globals(), local_vars)
        
        # 获取函数并应用
        indicator_function = local_vars[function_name]
        result_df = indicator_function(df.copy())
        
        return result_df
    
    def save_indicator(self, description: str, code: str, name: str, directory: str = "indicators") -> str:
        """
        保存生成的指标代码到文件
        
        参数:
            description (str): 指标的自然语言描述
            code (str): 生成的 Python 代码
            name (str): 指标名称
            directory (str): 保存目录
            
        返回:
            str: 保存的文件路径
        """
        os.makedirs(directory, exist_ok=True)
        
        # 创建文件名
        file_name = f"{name.lower().replace(' ', '_')}.py"
        file_path = os.path.join(directory, file_name)
        
        # 添加描述注释
        full_code = f'''"""
{name}

描述:
{description}

生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import pandas as pd
import numpy as np

{code}
'''
        
        with open(file_path, 'w') as f:
            f.write(full_code)
        
        return file_path
