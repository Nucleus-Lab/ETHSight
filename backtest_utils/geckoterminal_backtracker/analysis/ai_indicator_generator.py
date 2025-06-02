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
1. 函数应该接受一个 pandas DataFrame 作为输入，该 DataFrame 包含open,high,low,close,volume,datetime列
2. 函数应该返回原始 DataFrame，但添加了新的指标列
3. 使用 pandas 和 numpy 进行计算
4. 函数名应该反映指标的用途
5. 包含详细的文档字符串，解释指标的计算方法和用途
6. 代码应该高效且易于理解
7. 只返回 Python 代码，不要包含任何其他解释

交易信号生成规则（非常重要）:
1. 必须创建名为 'buy_signal' 的列来生成买入信号，值为 1 表示买入信号，值为 0 表示无信号
2. 必须创建名为 'sell_signal' 的列来生成卖出信号，值为 1 表示卖出信号，值为 0 表示无信号
3. 如果你的指标只生成买入信号，仍然需要创建空的 'sell_signal' 列（全部为 0）
4. 如果你的指标只生成卖出信号，仍然需要创建空的 'buy_signal' 列（全郦为 0）
5. 信号列的数据类型必须为整数（int），不要使用布尔值或浮点数
6. 最后要运行这个函数，我会传入外参 df，你只需要直接运行函数就行

示例（买卖信号生成）:
```python
# 生成买入信号
# 当满足某些条件时，设置买入信号为 1
# 例如：当 RSI < 30 且成交量增加时

df['buy_signal'] = 0  # 初始化买入信号列为 0
df.loc[(df['rsi'] < 30) & (df['volume_change'] > 0.1), 'buy_signal'] = 1

# 生成卖出信号
# 当满足某些条件时，设置卖出信号为 1
# 例如：当 RSI > 70 且成交量下降时

df['sell_signal'] = 0  # 初始化卖出信号列为 0
df.loc[(df['rsi'] > 70) & (df['volume_change'] < -0.1), 'sell_signal'] = 1
```

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

calculate_indicator(df)
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

    def generate_signal_calculation_code(self, signal_description: str, signal_name: str, model: str = "gpt-4o") -> str:
        """
        根据信号描述生成仅用于计算信号值的代码
        
        参数:
            signal_description (str): 信号的自然语言描述
            signal_name (str): 信号名称（将用作列名）
            model (str): 要使用的 OpenAI 模型
            
        返回:
            str: 生成的 Python 代码，用于计算信号值
        """
        prompt = self._create_signal_calculation_prompt(signal_description, signal_name)
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的金融技术指标开发专家，精通 Python 和 pandas。你的任务是将用户的信号描述转换为可执行的 Python 代码，用于计算金融信号值。代码应该接受一个包含 OHLC (Open, High, Low, Close) 和 Volume 列的 pandas DataFrame，计算信号值并返回DataFrame和信号列名。"},
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
    
    def _create_signal_calculation_prompt(self, signal_description: str, signal_name: str) -> str:
        """
        创建用于信号计算的提示
        
        参数:
            signal_description (str): 信号的自然语言描述
            signal_name (str): 信号名称
            
        返回:
            str: 格式化的提示
        """
        return f"""
请根据以下描述创建一个计算金融信号值的 Python 函数:

信号描述: {signal_description}
信号名称: {signal_name}

要求:
1. 函数应该接受一个 pandas DataFrame 作为输入，该 DataFrame 包含 open, high, low, close, volume, datetime 列
2. **首先检查 DataFrame 中是否已经存在与所需信号相匹配的列**
   - 检查是否有列名与 '{signal_name}' 相同或相似
   - 检查是否有其他列可以直接用作此信号（例如，如果需要 'volume' 信号，而 DataFrame 中已有 'volume' 列）
   - 如果找到合适的现有列，直接返回该列名，不要重新计算
3. 如果没有找到现有的合适列，则计算信号值并添加到 DataFrame 中，列名为 '{signal_name}'
4. 函数应该返回 (df, signal_column_name) 元组，其中 df 是包含信号列的 DataFrame，signal_column_name 是信号列的名称
5. 使用 pandas 和 numpy 进行计算
6. 函数名应该是 calculate_signal
7. 包含详细的文档字符串，解释信号的计算方法
8. 代码应该高效且易于理解
9. 只返回 Python 代码，不要包含任何其他解释
10. 不要生成买入/卖出信号，只计算信号的数值

重要说明:
- **优先使用现有列**: 如果 DataFrame 中已有相关列，优先使用而不是重复计算
- 只计算信号的数值，不要生成买入或卖出信号（不要创建 buy_signal 或 sell_signal 列）
- 信号值应该是数值类型（float 或 int），可以是连续值
- 例如：如果是成交量信号，返回成交量的值；如果是 RSI，返回 RSI 的值；如果是价格变化，返回价格变化的百分比等

示例函数格式:
```python
def calculate_signal(df):
    \"\"\"
    计算{signal_name}信号值
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame
        
    返回:
        tuple: (df_with_signal, signal_column_name)
            - df_with_signal: 包含信号列的 DataFrame
            - signal_column_name: 信号列的名称
    \"\"\"
    # 首先检查是否已存在相关列
    existing_columns = df.columns.tolist()
    
    # 检查是否有匹配的现有列
    ...
    
    # 如果没有找到现有列，计算新的信号值
    df['{signal_name}'] = ...  # 计算逻辑
    
    return df, '{signal_name}'

# 执行函数
df, signal_column = calculate_signal(df)
```

请只返回 Python 代码，不要包含任何其他解释。确保最后一行执行函数调用。确保首先检查现有列，避免不必要的重复计算。
不要在你的代码里定义df，之后调用你生成的代码的时候自然会有满足条件的df。
"""
