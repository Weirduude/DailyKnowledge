"""
Database models and operations for DailyKnowledge system.
Uses SQLite for simple, file-based storage.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_PATH, REVIEW_INTERVALS


@dataclass
class KnowledgeCard:
    """Represents a knowledge card in the database."""

    id: Optional[int]
    topic: str
    category: str
    summary: str
    created_at: date
    next_review_date: date
    review_stage: int

    @classmethod
    def from_row(cls, row: tuple) -> "KnowledgeCard":
        """Create a KnowledgeCard from a database row."""
        return cls(
            id=row[0],
            topic=row[1],
            category=row[2],
            summary=row[3],
            created_at=date.fromisoformat(row[4]) if row[4] else date.today(),
            next_review_date=date.fromisoformat(row[5]) if row[5] else date.today(),
            review_stage=row[6],
        )


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the file if needed."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def init_database() -> None:
    """Initialize the database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                summary TEXT,
                created_at DATE NOT NULL,
                next_review_date DATE NOT NULL,
                review_stage INTEGER DEFAULT 0
            )
        """
        )
        # Create index for efficient review queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_next_review_date 
            ON knowledge_cards(next_review_date)
        """
        )
        conn.commit()


def get_learned_topics() -> set[str]:
    """Get all topics that have already been learned.

    Returns:
        Set of topic names already in the database.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT topic FROM knowledge_cards")
        return {row[0] for row in cursor.fetchall()}


def get_unlearned_topics(all_topics: list[dict]) -> list[dict]:
    """Get topics that haven't been learned yet.

    Args:
        all_topics: List of all available topics from topics.json

    Returns:
        List of topics not yet in the database.
    """
    learned = get_learned_topics()
    return [t for t in all_topics if t["topic"] not in learned]


def get_due_reviews(target_date: Optional[date] = None) -> list[KnowledgeCard]:
    """Get all cards due for review on or before the target date.

    Args:
        target_date: The date to check for due reviews. Defaults to today.

    Returns:
        List of KnowledgeCard objects due for review.
    """
    if target_date is None:
        target_date = date.today()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, topic, category, summary, created_at, next_review_date, review_stage
            FROM knowledge_cards
            WHERE next_review_date <= ?
            ORDER BY next_review_date ASC
        """,
            (target_date.isoformat(),),
        )

        return [KnowledgeCard.from_row(row) for row in cursor.fetchall()]


def add_knowledge_card(
    topic: str, category: str, summary: str, created_at: Optional[date] = None
) -> KnowledgeCard:
    """Add a new knowledge card to the database.

    Args:
        topic: The knowledge topic name.
        category: The category (Foundations, Engineering, etc.)
        summary: LLM-generated summary (<50 words).
        created_at: Date of initial learning. Defaults to today.

    Returns:
        The created KnowledgeCard object.
    """
    if created_at is None:
        created_at = date.today()

    # First review is after 1 day (stage 0 -> interval[0])
    next_review = created_at + timedelta(days=REVIEW_INTERVALS[0])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO knowledge_cards 
            (topic, category, summary, created_at, next_review_date, review_stage)
            VALUES (?, ?, ?, ?, ?, 0)
        """,
            (topic, category, summary, created_at.isoformat(), next_review.isoformat()),
        )
        conn.commit()

        card_id = cursor.lastrowid

    return KnowledgeCard(
        id=card_id,
        topic=topic,
        category=category,
        summary=summary,
        created_at=created_at,
        next_review_date=next_review,
        review_stage=0,
    )


def update_review_stage(card_id: int) -> Optional[KnowledgeCard]:
    """Update a card's review stage after successful review.

    Moves to the next Ebbinghaus interval, or marks as completed
    if at the final stage.

    Args:
        card_id: The ID of the card to update.

    Returns:
        Updated KnowledgeCard, or None if not found.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get current card
        cursor.execute(
            """
            SELECT id, topic, category, summary, created_at, next_review_date, review_stage
            FROM knowledge_cards WHERE id = ?
        """,
            (card_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        card = KnowledgeCard.from_row(row)

        # Calculate next stage and review date
        new_stage = card.review_stage + 1

        if new_stage < len(REVIEW_INTERVALS):
            # Schedule next review based on interval
            next_review = date.today() + timedelta(days=REVIEW_INTERVALS[new_stage])
        else:
            # Completed all stages - set far future date (effectively "graduated")
            next_review = date.today() + timedelta(days=365)
            new_stage = len(REVIEW_INTERVALS)  # Cap at max stage

        cursor.execute(
            """
            UPDATE knowledge_cards 
            SET review_stage = ?, next_review_date = ?
            WHERE id = ?
        """,
            (new_stage, next_review.isoformat(), card_id),
        )
        conn.commit()

        card.review_stage = new_stage
        card.next_review_date = next_review
        return card


def get_all_cards() -> list[KnowledgeCard]:
    """Get all knowledge cards from the database.

    Returns:
        List of all KnowledgeCard objects.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, topic, category, summary, created_at, next_review_date, review_stage
            FROM knowledge_cards
            ORDER BY created_at DESC
        """
        )
        return [KnowledgeCard.from_row(row) for row in cursor.fetchall()]


def get_card_by_topic(topic: str) -> Optional[KnowledgeCard]:
    """Get a knowledge card by its topic name.

    Args:
        topic: The topic name to search for.

    Returns:
        KnowledgeCard if found, None otherwise.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, topic, category, summary, created_at, next_review_date, review_stage
            FROM knowledge_cards WHERE topic = ?
        """,
            (topic,),
        )

        row = cursor.fetchone()
        return KnowledgeCard.from_row(row) if row else None
