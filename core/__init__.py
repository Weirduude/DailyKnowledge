"""Core module for DailyKnowledge system."""

from core.selector import select_new_topic, select_due_reviews
from core.generator import generate_new_knowledge, generate_review_question
from core.messenger import send_daily_email, render_email_html
from core.recorder import record_new_learning, record_review_completion

__all__ = [
    "select_new_topic",
    "select_due_reviews",
    "generate_new_knowledge",
    "generate_review_question",
    "send_daily_email",
    "render_email_html",
    "record_new_learning",
    "record_review_completion",
]
