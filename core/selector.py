"""
Topic selector module.
Supports both static topic list and dynamic LLM-based topic generation.
Implements Ebbinghaus-based review scheduling.
"""

import json
import random
from datetime import date
from pathlib import Path
from typing import Optional

from openai import OpenAI

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TOPICS_PATH, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from database.models import (
    get_unlearned_topics,
    get_due_reviews,
    get_learned_topics,
    get_all_cards,
    KnowledgeCard,
)


# ==================== Dynamic Topic Generation ====================


def _get_client() -> OpenAI:
    """Get OpenAI API client."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")
    return OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
    )


def generate_dynamic_topic() -> Optional[dict]:
    """Use LLM to dynamically generate a new topic based on user profile.

    This is the recommended approach for personalized learning.
    The LLM considers:
    - User's background and expertise level
    - Already learned topics (to avoid repetition)
    - Current AI trends and important concepts

    Returns:
        A topic dictionary with 'topic', 'category', 'why', etc.
        or None if generation fails.
    """
    from prompts.topic_generator import (
        TOPIC_GENERATOR_SYSTEM_PROMPT,
        TOPIC_GENERATOR_USER_TEMPLATE,
    )
    from user_profile import USER_PROFILE, INTERESTS, SKIP_TOPICS

    # Get already learned topics
    learned = get_learned_topics()
    learned_list = sorted(learned) if learned else ["（尚无学习记录）"]

    # Calculate streak days (simplified)
    cards = get_all_cards()
    streak_days = len(set(c.created_at for c in cards)) if cards else 0

    # Format the system prompt with user profile
    system_prompt = TOPIC_GENERATOR_SYSTEM_PROMPT.format(
        user_profile=USER_PROFILE,
        learned_topics="\n".join(f"- {t}" for t in learned_list[-50:]),  # Last 50
    )

    # Format user prompt
    user_prompt = TOPIC_GENERATOR_USER_TEMPLATE.format(
        date=date.today().strftime("%Y-%m-%d"),
        learned_count=len(learned),
        streak_days=streak_days,
    )

    # Add interests context
    if INTERESTS:
        user_prompt += f"\n\n我目前比较关注：{', '.join(INTERESTS)}"
    if SKIP_TOPICS:
        user_prompt += f"\n请避开这些我已熟悉的方向：{', '.join(SKIP_TOPICS)}"

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,  # Higher for diversity
            max_tokens=500,
        )

        # Parse JSON response
        text = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        topic_data = json.loads(text)

        # Validate required fields
        if "topic" not in topic_data or "category" not in topic_data:
            raise ValueError("Missing required fields in response")

        return topic_data

    except Exception as e:
        import logging

        logging.warning(f"Dynamic topic generation failed: {e}")
        logging.warning("Falling back to static topic selection...")
        return None


# ==================== Static Topic Selection (Legacy) ====================


def load_all_topics() -> list[dict]:
    """Load all topics from the topics.json file (legacy/fallback).

    Returns:
        List of topic dictionaries with 'topic' and 'category' keys.
    """
    if not TOPICS_PATH.exists():
        return []  # Return empty list instead of raising error

    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("topics", [])


def select_static_topic() -> Optional[dict]:
    """Select a random unlearned topic from static list (legacy/fallback).

    Returns:
        A topic dictionary with 'topic' and 'category' keys,
        or None if all topics have been learned.
    """
    all_topics = load_all_topics()
    if not all_topics:
        return None

    unlearned = get_unlearned_topics(all_topics)

    if not unlearned:
        return None

    return random.choice(unlearned)


# ==================== Main Selection Interface ====================


def select_new_topic(use_dynamic: bool = True) -> Optional[dict]:
    """Select a new topic for today's learning.

    Args:
        use_dynamic: If True, use LLM to generate topic dynamically.
                    If False or if dynamic fails, fall back to static list.

    Returns:
        A topic dictionary with 'topic' and 'category' keys.
    """
    import logging

    if use_dynamic:
        topic = generate_dynamic_topic()
        if topic:
            logging.info(f"[Dynamic] Generated topic: {topic.get('topic')}")
            return topic
        # Fallback message already logged in generate_dynamic_topic()

    return select_static_topic()


def select_due_reviews(target_date: Optional[date] = None) -> list[KnowledgeCard]:
    """Select all cards due for review today.

    Based on the Ebbinghaus forgetting curve, cards are scheduled
    for review at intervals: 1, 2, 4, 7, 15, 30, 60 days.

    Args:
        target_date: The date to check for due reviews. Defaults to today.

    Returns:
        List of KnowledgeCard objects due for review.
    """
    return get_due_reviews(target_date)


def get_topic_stats() -> dict:
    """Get statistics about learning progress.

    Returns:
        Dictionary with learning statistics.
    """
    # Get stats from database (dynamic mode)
    cards = get_all_cards()
    learned_topics = get_learned_topics()

    # Count by category from learned cards
    category_counts = {}
    for card in cards:
        cat = card.category
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # For dynamic mode, we don't have a fixed "total"
    # Just show what we've learned
    return {
        "total_topics": "∞",  # Dynamic mode has no upper limit
        "learned_topics": len(learned_topics),
        "unlearned_topics": "∞",
        "total_by_category": category_counts,
        "unlearned_by_category": {},
        "progress_percent": None,  # No percentage in dynamic mode
        "mode": "dynamic",
    }


def get_topic_stats_static() -> dict:
    """Get statistics for static topic mode (legacy).

    Returns:
        Dictionary with counts by category and overall progress.
    """
    all_topics = load_all_topics()
    if not all_topics:
        return get_topic_stats()  # Fall back to dynamic stats

    unlearned = get_unlearned_topics(all_topics)

    # Count by category
    total_by_category = {}
    for topic in all_topics:
        cat = topic.get("category", "Unknown")
        total_by_category[cat] = total_by_category.get(cat, 0) + 1

    unlearned_by_category = {}
    for topic in unlearned:
        cat = topic.get("category", "Unknown")
        unlearned_by_category[cat] = unlearned_by_category.get(cat, 0) + 1

    return {
        "total_topics": len(all_topics),
        "learned_topics": len(all_topics) - len(unlearned),
        "unlearned_topics": len(unlearned),
        "total_by_category": total_by_category,
        "unlearned_by_category": unlearned_by_category,
        "progress_percent": (
            round((len(all_topics) - len(unlearned)) / len(all_topics) * 100, 1)
            if all_topics
            else 0
        ),
        "mode": "static",
    }
