from geckoterminal_backtracker.analysis.ai_indicator_generator import AIIndicatorGenerator
import os

# 获取 API 密钥
api_key = os.getenv("OPENAI_API_KEY")

description = "创建一个结合RSI和成交量的动量指标，当指标值超过70时产生卖出信号，低于30时产生买入信号"

# 创建生成器实例
# 生成指标代码
# TODO: 
generator = AIIndicatorGenerator(api_key)
code = generator.generate_indicator_code(description)

# 打印或使用生成的代码
print(code)