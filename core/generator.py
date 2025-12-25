"""
Content generator module.
Handles LLM API calls for generating new knowledge and review questions.
Supports OpenAI-compatible APIs (OpenAI, Azure, DeepSeek, local models, etc.)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openai import OpenAI

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS,
    CATEGORIES,
    REVIEW_INTERVALS,
)
from database.models import KnowledgeCard
from prompts import (
    NEWSLETTER_SYSTEM_PROMPT,
    NEWSLETTER_USER_TEMPLATE,
    EXAMINER_SYSTEM_PROMPT,
    EXAMINER_USER_TEMPLATE,
)


@dataclass
class GeneratedContent:
    """Container for generated content."""

    topic: str
    category: str
    content: str
    summary: str  # Extracted TL;DR for database storage


# Global client instance
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Get or create OpenAI API client."""
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        _client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )
    return _client


def _extract_summary(content: str) -> str:
    """Extract the TL;DR summary from generated content.

    Args:
        content: Full generated markdown content.

    Returns:
        Extracted summary string, or empty string if not found.
    """
    # Look for the TL;DR section
    patterns = [
        r"###\s*⚡\s*速记总结.*?\n(.+?)(?:\n###|\n##|$)",
        r"\*\*TL;DR\*\*[：:]\s*(.+?)(?:\n|$)",
        r"速记总结[：:]\s*(.+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            summary = match.group(1).strip()
            # Clean up markdown formatting
            summary = re.sub(r"\*+", "", summary)
            summary = re.sub(r"\s+", " ", summary)
            return summary[:200]  # Limit length

    return ""


def generate_new_knowledge(
    topic: str, category: str, why: str = ""
) -> GeneratedContent:
    """Generate new knowledge content for a topic.

    Args:
        topic: The knowledge topic name.
        category: The category (Foundations, Engineering, etc.)
        why: Optional reason why this topic is recommended.

    Returns:
        GeneratedContent with full article and extracted summary.

    Raises:
        ValueError: If API key is not configured.
        Exception: If API call fails.
    """
    client = _get_client()

    # Get category info for context
    category_info = CATEGORIES.get(category, {})
    emoji = category_info.get("emoji", "📚")
    description = category_info.get("description", category)

    # Format user prompt
    user_prompt = NEWSLETTER_USER_TEMPLATE.format(
        topic=topic,
        category=f"{emoji} {category} - {description}",
        why=why or "这是一个值得深入学习的AI技术概念",
    )

    # Generate content using OpenAI API
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": NEWSLETTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=OPENAI_TEMPERATURE,
        max_tokens=OPENAI_MAX_TOKENS,
    )

    content = response.choices[0].message.content
    summary = _extract_summary(content)

    return GeneratedContent(
        topic=topic,
        category=category,
        content=content,
        summary=summary or f"关于{topic}的核心概念",
    )


def generate_review_question(card: KnowledgeCard) -> str:
    """Generate a review question for a knowledge card.

    Args:
        card: The KnowledgeCard to generate a review question for.

    Returns:
        Generated review question as markdown string.

    Raises:
        ValueError: If API key is not configured.
        Exception: If API call fails.
    """
    client = _get_client()

    # Get category info
    category_info = CATEGORIES.get(card.category, {})
    emoji = category_info.get("emoji", "📚")

    # Calculate review interval
    stage = card.review_stage
    interval = (
        REVIEW_INTERVALS[stage]
        if stage < len(REVIEW_INTERVALS)
        else REVIEW_INTERVALS[-1]
    )

    # Format user prompt
    user_prompt = EXAMINER_USER_TEMPLATE.format(
        topic=card.topic,
        category=f"{emoji} {card.category}",
        summary=card.summary or "（无速记内容）",
        created_at=card.created_at.isoformat(),
        stage=stage + 1,  # Human-readable (1-indexed)
        interval=interval,
    )

    # Generate content using OpenAI API
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": EXAMINER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,  # Slightly higher for variety in questions
        max_tokens=1000,
    )

    return response.choices[0].message.content


def test_api_connection() -> bool:
    """Test if the OpenAI API is properly configured.

    Returns:
        True if API is working, False otherwise.
    """
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'API connection successful' in one line.",
                }
            ],
            max_tokens=50,
        )
        return bool(response.choices[0].message.content)
    except Exception as e:
        print(f"API test failed: {e}")
        return False
