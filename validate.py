#!/usr/bin/env python3
"""
Quick validation script for DailyKnowledge system.
Run this to verify the project structure and basic functionality.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def check_imports():
    """Verify all modules can be imported."""
    print("🔍 Checking module imports...")

    modules = [
        ("config", "Configuration"),
        ("database", "Database"),
        ("database.models", "Database Models"),
        ("core.selector", "Selector"),
        ("core.generator", "Generator"),
        ("core.messenger", "Messenger"),
        ("core.recorder", "Recorder"),
        ("prompts", "Prompts"),
        ("prompts.topic_generator", "Topic Generator"),
        ("user_profile", "User Profile"),
    ]

    all_ok = True
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name}")
        except ImportError as e:
            print(f"  ❌ {display_name}: {e}")
            all_ok = False

    return all_ok


def check_files():
    """Verify all required files exist."""
    print("\n📁 Checking required files...")

    base = Path(__file__).parent
    files = [
        "config.py",
        "main.py",
        "user_profile.py",
        "requirements.txt",
        ".env.example",
        "data/topics.json",
        "database/__init__.py",
        "database/models.py",
        "core/__init__.py",
        "core/selector.py",
        "core/generator.py",
        "core/messenger.py",
        "core/recorder.py",
        "prompts/__init__.py",
        "prompts/newsletter.py",
        "prompts/examiner.py",
        "prompts/topic_generator.py",
        ".github/workflows/daily_knowledge.yml",
    ]

    all_ok = True
    for file in files:
        path = base / file
        if path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - NOT FOUND")
            all_ok = False

    return all_ok


def check_topics():
    """Verify topics.json is valid."""
    print("\n📚 Checking topics database...")

    import json

    base = Path(__file__).parent
    topics_path = base / "data" / "topics.json"

    try:
        with open(topics_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        topics = data.get("topics", [])
        categories = {}

        for topic in topics:
            cat = topic.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1

        print(f"  📖 Total topics: {len(topics)}")
        for cat, count in sorted(categories.items()):
            print(f"     - {cat}: {count}")

        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_database():
    """Verify database can be initialized."""
    print("\n💾 Checking database...")

    try:
        from database import init_database

        init_database()
        print("  ✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


def main():
    print("=" * 50)
    print("🧠 DailyKnowledge System Validation")
    print("=" * 50)

    results = []
    results.append(check_imports())
    results.append(check_files())
    results.append(check_topics())
    results.append(check_database())

    print("\n" + "=" * 50)
    if all(results):
        print("✅ All checks passed! System is ready.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and fill in your credentials")
        print("2. Run: python main.py --test")
        print("3. Run: python main.py --dry-run")
        print("4. Run: python main.py")
    else:
        print("❌ Some checks failed. Please review the errors above.")
    print("=" * 50)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
