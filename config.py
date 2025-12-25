"""
Configuration management for DailyKnowledge system.
Uses environment variables for sensitive data.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==================== Path Configuration ====================
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "database" / "knowledge.db"
TOPICS_PATH = BASE_DIR / "data" / "topics.json"

# ==================== LLM Configuration (OpenAI Compatible) ====================
# API Key from environment variable (sensitive)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Configurable settings (not sensitive, can be in config)
OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL", "https://api.openai.com/v1"
)  # Custom endpoint
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Model name
OPENAI_TEMPERATURE = float(
    os.getenv("OPENAI_TEMPERATURE", "0.7")
)  # Default temperature
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "3000"))  # Max output tokens

# ==================== Email Configuration ====================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # App-specific password
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")  # Comma-separated for multiple recipients

# ==================== Ebbinghaus Review Intervals ====================
# Days after initial learning for each review stage
REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30, 60]  # Stage 0-6

# ==================== Content Categories ====================
# Extended categories for dynamic topic generation
CATEGORIES = {
    # Original categories
    "Foundations": {
        "emoji": "🟢",
        "description": "数学与底层原理",
    },
    "Engineering": {
        "emoji": "🔵",
        "description": "落地与系统优化",
    },
    "SOTA": {
        "emoji": "🟣",
        "description": "前沿技术点",
    },
    "Reasoning": {
        "emoji": "🟠",
        "description": "Agent 与 Prompt",
    },
    "History": {
        "emoji": "🟡",
        "description": "历史与行业八卦",
    },
    # Extended categories for dynamic generation
    "Architecture": {
        "emoji": "🏗️",
        "description": "模型架构创新",
    },
    "Training": {
        "emoji": "⚙️",
        "description": "训练方法与技巧",
    },
    "Alignment": {
        "emoji": "🎯",
        "description": "对齐与安全",
    },
    "Efficiency": {
        "emoji": "⚡",
        "description": "高效推理与部署",
    },
    "Multimodal": {
        "emoji": "🎨",
        "description": "多模态学习",
    },
    "Agent": {
        "emoji": "🤖",
        "description": "智能体系统",
    },
    "Generation": {
        "emoji": "✨",
        "description": "生成模型",
    },
    "Application": {
        "emoji": "💼",
        "description": "应用领域",
    },
    "Frontier": {
        "emoji": "🚀",
        "description": "前沿热点",
    },
    "General": {
        "emoji": "📚",
        "description": "通用知识",
    },
}


def validate_config() -> list[str]:
    """Validate required configuration values.

    Returns:
        List of missing configuration keys.
    """
    errors = []

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is not set")

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        errors.append("SMTP credentials are not configured")

    if not EMAIL_FROM or not EMAIL_TO:
        errors.append("Email addresses are not configured")

    return errors
