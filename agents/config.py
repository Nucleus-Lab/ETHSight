from typing import Dict, Any
from enum import Enum
import os

class ModelConfig(str, Enum):
    """Enum for different LLM models"""
    HAIKU = "claude-3-5-haiku"
    SONNET = "claude-3-7-sonnet"
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"

# Configuration for different LLM models
LLM_CONFIGS: Dict[ModelConfig, Dict[str, Any]] = {
    ModelConfig.HAIKU: {
        "model_name": "haiku",
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "base_url": os.getenv("ANTHROPIC_BASE_URL"),
    },
    ModelConfig.SONNET: {
        "model_name": "sonnet",
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "base_url": os.getenv("ANTHROPIC_BASE_URL"),
    },
    ModelConfig.GPT4O: {
        "model_name": "gpt-4o",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL"),
    },
    ModelConfig.GPT4O_MINI: {
        "model_name": "gpt-4o-mini",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL"),
    }
}

def get_model_config(model_config: ModelConfig) -> Dict[str, Any]:
    return LLM_CONFIGS.get(model_config)
