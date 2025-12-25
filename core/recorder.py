"""
Recorder module.
Handles database updates after learning and review activities.
"""

from datetime import date
from pathlib import Path
from typing import Optional

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.models import (
    add_knowledge_card,
    update_review_stage,
    KnowledgeCard,
)


def record_new_learning(
    topic: str, category: str, summary: str, learned_date: Optional[date] = None
) -> KnowledgeCard:
    """Record a new knowledge learning event.

    Creates a new knowledge card in the database and schedules
    the first review based on Ebbinghaus intervals.

    Args:
        topic: The knowledge topic name.
        category: The category (Foundations, Engineering, etc.)
        summary: LLM-generated summary for quick recall.
        learned_date: Date of learning. Defaults to today.

    Returns:
        The created KnowledgeCard object.
    """
    return add_knowledge_card(
        topic=topic, category=category, summary=summary, created_at=learned_date
    )


def record_review_completion(card_id: int) -> Optional[KnowledgeCard]:
    """Record a review completion event.

    Updates the card's review stage and schedules the next review
    based on Ebbinghaus intervals.

    Args:
        card_id: The ID of the reviewed card.

    Returns:
        Updated KnowledgeCard, or None if not found.
    """
    return update_review_stage(card_id)


def batch_record_reviews(card_ids: list[int]) -> list[KnowledgeCard]:
    """Record multiple review completions.

    Args:
        card_ids: List of card IDs that were reviewed.

    Returns:
        List of updated KnowledgeCard objects.
    """
    results = []
    for card_id in card_ids:
        card = record_review_completion(card_id)
        if card:
            results.append(card)
    return results
