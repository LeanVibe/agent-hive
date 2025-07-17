#!/usr/bin/env python3
"""
Test script to demonstrate prompt logging functionality
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dashboard.prompt_logger import prompt_logger

def test_prompt_logging():
    """Test prompt logging functionality"""

    # Log some sample prompts
    print("🧪 Testing prompt logging...")

    # Test successful prompt
    log_id1 = prompt_logger.log_prompt(
        "documentation-agent",
        "Hello! I'm ready to work on documentation tasks. Please provide me with specific requirements.",
        "Great! I'll start working on the documentation structure.",
        True
    )

    # Test failed prompt
    log_id2 = prompt_logger.log_prompt(
        "integration-agent",
        "Can you help me integrate with external APIs?",
        "",
        False,
        "Connection timeout error"
    )

    # Test another successful prompt
    log_id3 = prompt_logger.log_prompt(
        "pm-agent",
        "Review the current sprint progress and update GitHub issues",
        "I've reviewed the sprint. All tasks are on track.",
        True
    )

    print(f"✅ Logged {log_id3} prompts")

    # Test getting recent prompts
    recent_prompts = prompt_logger.get_recent_prompts(10)
    print(f"📋 Recent prompts: {len(recent_prompts)}")

    for prompt in recent_prompts:
        status = "✅" if prompt.success else "❌"
        print(f"  {status} {prompt.agent_name}: {prompt.prompt_text[:50]}...")

    # Test statistics
    stats = prompt_logger.get_prompt_stats()
    print(f"📊 Statistics:")
    print(f"  Total prompts: {stats['total_prompts']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Needs review: {stats['needs_review']}")
    print(f"  Agent breakdown: {stats['agent_stats']}")

    # Test adding PM review
    prompt_logger.add_pm_review(
        log_id2,
        "This prompt failed due to network issues. The agent should have better error handling.",
        "Add retry logic and better error messages: 'Can you help me integrate with external APIs? Please retry if there are connection issues and provide detailed error information.'"
    )

    print("✅ Added PM review to failed prompt")

    # Test Gemini feedback
    prompt_logger.add_gemini_feedback(
        log_id1,
        "Good starting prompt. Clear and actionable. Could be more specific about documentation type needed."
    )

    print("✅ Added Gemini feedback")

    # Test prompts needing review
    needs_review = prompt_logger.get_prompts_needing_review()
    print(f"📝 Prompts needing review: {len(needs_review)}")

if __name__ == "__main__":
    test_prompt_logging()
