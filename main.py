#!/usr/bin/env python3
"""
DailyKnowledge - AI Knowledge Daily Push System

Main entry point for the daily knowledge workflow:
1. Select a new topic to learn (dynamic LLM-based or static list)
2. Generate knowledge content via LLM
3. Select due reviews based on Ebbinghaus curve
4. Generate review questions via LLM
5. Send email with all content
6. Update database with new learning and completed reviews
"""
import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import validate_config, CATEGORIES
from database import init_database, get_all_cards
from core.selector import select_new_topic, select_due_reviews, get_topic_stats
from core.generator import (
    generate_new_knowledge,
    generate_review_question,
    test_api_connection,
)
from core.messenger import send_daily_email, render_email_html
from core.recorder import record_new_learning, batch_record_reviews

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("daily_knowledge.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_daily_workflow(
    dry_run: bool = False, skip_email: bool = False, use_dynamic: bool = True
) -> bool:
    """Execute the daily knowledge workflow.

    Args:
        dry_run: If True, don't send email or update database.
        skip_email: If True, skip email sending but still update database.
        use_dynamic: If True, use LLM to generate topics dynamically.

    Returns:
        True if workflow completed successfully.
    """
    mode = "Dynamic" if use_dynamic else "Static"
    logger.info("=" * 50)
    logger.info(f"Starting daily knowledge workflow - {date.today()}")
    logger.info(f"Mode: {mode} topic selection")
    logger.info("=" * 50)

    # Validate configuration
    errors = validate_config()
    if errors and not dry_run:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return False

    # Initialize database
    init_database()
    logger.info("Database initialized")

    # Get current stats
    stats = get_topic_stats()
    logger.info(f"已学习 {stats['learned_topics']} 个主题")

    # ==================== Select New Topic ====================
    new_topic_info = select_new_topic(use_dynamic=use_dynamic)
    new_content = None
    new_topic = None
    new_category = None
    new_summary = None
    topic_why = None

    if new_topic_info:
        new_topic = new_topic_info["topic"]
        new_category = new_topic_info.get("category", "General")
        topic_why = new_topic_info.get("why", "")

        logger.info(f"Selected new topic: {new_topic} ({new_category})")
        if topic_why:
            logger.info(f"Why: {topic_why}")

        # Generate content
        try:
            result = generate_new_knowledge(new_topic, new_category, why=topic_why)
            new_content = result.content
            new_summary = result.summary
            logger.info(f"Generated content for: {new_topic}")
            logger.info(f"Summary: {new_summary[:100]}...")
        except Exception as e:
            logger.error(f"Failed to generate new content: {e}")
            if not dry_run:
                raise
    else:
        logger.info("No new topics available - all topics have been learned!")

    # ==================== Select Due Reviews ====================
    due_reviews = select_due_reviews()
    review_contents = []
    reviewed_card_ids = []

    if due_reviews:
        logger.info(f"Found {len(due_reviews)} cards due for review")

        for card in due_reviews:
            try:
                review_content = generate_review_question(card)
                review_contents.append(review_content)
                reviewed_card_ids.append(card.id)
                logger.info(
                    f"Generated review for: {card.topic} (stage {card.review_stage})"
                )
            except Exception as e:
                logger.error(f"Failed to generate review for {card.topic}: {e}")
    else:
        logger.info("No reviews due today")

    # ==================== Send Email ====================
    if not dry_run and not skip_email:
        # Re-fetch stats after potential changes
        stats = get_topic_stats()

        success = send_daily_email(
            new_content=new_content,
            new_topic=new_topic,
            new_category=new_category,
            review_contents=review_contents if review_contents else None,
            stats=stats,
        )

        if success:
            logger.info("Email sent successfully!")
        else:
            logger.error("Failed to send email")
            return False
    elif dry_run:
        logger.info("[DRY RUN] Would send email with:")
        logger.info(f"  - New topic: {new_topic}")
        logger.info(f"  - Review questions: {len(review_contents)}")

        # Save HTML preview for dry run
        html = render_email_html(
            new_content=new_content,
            new_topic=new_topic,
            new_category=new_category,
            review_contents=review_contents if review_contents else None,
            stats=stats,
        )
        preview_path = Path("email_preview.html")
        preview_path.write_text(html, encoding="utf-8")
        logger.info(f"Email preview saved to: {preview_path.absolute()}")

    # ==================== Update Database ====================
    if not dry_run:
        # Record new learning
        if new_topic and new_summary:
            card = record_new_learning(new_topic, new_category, new_summary)
            logger.info(
                f"Recorded new learning: {card.topic} (next review: {card.next_review_date})"
            )

        # Record review completions
        if reviewed_card_ids:
            updated_cards = batch_record_reviews(reviewed_card_ids)
            for card in updated_cards:
                logger.info(
                    f"Updated review: {card.topic} -> stage {card.review_stage} (next: {card.next_review_date})"
                )

    logger.info("Daily workflow completed successfully!")
    return True


def show_status():
    """Display current learning status."""
    init_database()
    stats = get_topic_stats()

    print("\n" + "=" * 50)
    print("📊 DailyKnowledge Status")
    print("=" * 50)

    mode = stats.get("mode", "dynamic")
    if mode == "dynamic":
        print(f"\n🚀 Mode: Dynamic (LLM-powered topic generation)")
        print(f"   ✅ Topics Learned: {stats['learned_topics']}")
        print(f"   ∞  Unlimited exploration")
    else:
        print(f"\n📈 Overall Progress: {stats['progress_percent']}%")
        print(f"   ✅ Learned: {stats['learned_topics']}")
        print(f"   📚 Remaining: {stats['unlearned_topics']}")
        print(f"   📖 Total: {stats['total_topics']}")

    if stats["total_by_category"]:
        print("\n📁 Learned by Category:")
        for category, count in sorted(
            stats["total_by_category"].items(), key=lambda x: -x[1]
        ):
            emoji = CATEGORIES.get(category, {}).get("emoji", "📚")
            print(f"   {emoji} {category}: {count}")

    # Show due reviews
    due_reviews = select_due_reviews()
    if due_reviews:
        print(f"\n🔄 Due for Review Today: {len(due_reviews)}")
        for card in due_reviews[:5]:  # Show first 5
            emoji = CATEGORIES.get(card.category, {}).get("emoji", "📚")
            print(f"   {emoji} {card.topic} (stage {card.review_stage})")
        if len(due_reviews) > 5:
            print(f"   ... and {len(due_reviews) - 5} more")
    else:
        print("\n✨ No reviews due today!")

    print()


def test_connection():
    """Test API and email connections."""
    print("\n🔧 Testing connections...\n")

    # Test LLM API
    print("Testing LLM API (OpenAI Compatible)...")
    if test_api_connection():
        print("  ✅ LLM API: Connected")
    else:
        print("  ❌ LLM API: Failed")

    # Test SMTP connection
    print("\nTesting SMTP connection...")
    from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

    if SMTP_USERNAME and SMTP_PASSWORD:
        try:
            import smtplib
            import ssl

            if SMTP_PORT == 465:
                # SSL mode
                context = ssl.create_default_context()
                # Disable hostname checking for some Chinese email providers
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                with smtplib.SMTP_SSL(
                    SMTP_SERVER, SMTP_PORT, context=context, timeout=10
                ) as server:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                print(f"  ✅ SMTP: Connected ({SMTP_SERVER}:{SMTP_PORT} SSL)")
            else:
                # STARTTLS mode
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                print(f"  ✅ SMTP: Connected ({SMTP_SERVER}:{SMTP_PORT} STARTTLS)")
        except smtplib.SMTPAuthenticationError:
            print(
                "  ❌ SMTP: Authentication failed (check password/authorization code)"
            )
        except Exception as e:
            print(f"  ❌ SMTP: {e}")
    else:
        print("  ⚠️  SMTP: Credentials not configured")

    # Validate config
    errors = validate_config()
    if errors:
        print("\n⚠️  Configuration issues:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ All configuration validated")

    print()


def main():
    """Main entry point with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="DailyKnowledge - AI Knowledge Daily Push System"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without sending email or updating database",
    )

    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip email sending but still update database",
    )

    parser.add_argument(
        "--static",
        action="store_true",
        help="Use static topic list instead of dynamic LLM generation",
    )

    parser.add_argument(
        "--status", action="store_true", help="Show current learning status"
    )

    parser.add_argument(
        "--test", action="store_true", help="Test API and email connections"
    )

    parser.add_argument(
        "--init-db", action="store_true", help="Initialize database only"
    )

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.test:
        test_connection()
    elif args.init_db:
        init_database()
        print("Database initialized successfully!")
    else:
        success = run_daily_workflow(
            dry_run=args.dry_run,
            skip_email=args.skip_email,
            use_dynamic=not args.static,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
