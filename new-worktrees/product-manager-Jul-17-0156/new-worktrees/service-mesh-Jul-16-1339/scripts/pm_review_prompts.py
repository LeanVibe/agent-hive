#!/usr/bin/env python3
"""
PM Review Tool for Agent Prompts

Simple tool for PM to review prompts and suggest improvements.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dashboard.prompt_logger import prompt_logger

def review_prompts():
    """Interactive PM review of prompts"""

    prompts_needing_review = prompt_logger.get_prompts_needing_review()

    if not prompts_needing_review:
        print("✅ No prompts need review!")
        return

    print(f"📝 Found {len(prompts_needing_review)} prompts needing review")
    print("=" * 60)

    for i, prompt in enumerate(prompts_needing_review, 1):
        print(f"\n📋 PROMPT {i}/{len(prompts_needing_review)}")
        print(f"🤖 Agent: {prompt.agent_name}")
        print(f"⏰ Time: {prompt.timestamp}")
        print(f"✅ Success: {prompt.success}")

        if prompt.error_message:
            print(f"❌ Error: {prompt.error_message}")

        print(f"\n💬 Prompt:")
        print("-" * 40)
        print(prompt.prompt_text)
        print("-" * 40)

        if prompt.response_text:
            print(f"\n🤖 Response:")
            print("-" * 40)
            print(prompt.response_text[:200] + ("..." if len(prompt.response_text) > 200 else ""))
            print("-" * 40)

        if prompt.gemini_feedback:
            print(f"\n🧠 Gemini Feedback:")
            print(prompt.gemini_feedback)

        # Auto-review based on common patterns
        auto_review = generate_auto_review(prompt)
        print(f"\n🤖 Auto-Review Suggestion:")
        print(auto_review['review'])
        print(f"\n💡 Suggested Improvement:")
        print(auto_review['improvement'])

        # Option to accept auto-review or provide custom review
        try:
            choice = input(f"\n[A]ccept auto-review, [C]ustom review, [S]kip? (a/c/s): ").lower()

            if choice == 'a':
                prompt_logger.add_pm_review(
                    prompt.id,
                    auto_review['review'],
                    auto_review['improvement']
                )
                print("✅ Auto-review accepted and saved")

            elif choice == 'c':
                review = input("📝 Enter your review: ")
                improvement = input("💡 Enter suggested improvement: ")

                prompt_logger.add_pm_review(prompt.id, review, improvement)
                print("✅ Custom review saved")

            else:
                print("⏭ Skipped")

        except KeyboardInterrupt:
            print("\n\n👋 Review session cancelled")
            break
        except EOFError:
            print("\n\n👋 End of input")
            break

    print(f"\n✨ Review complete!")

def generate_auto_review(prompt):
    """Generate automatic review based on prompt patterns"""

    review_parts = []
    improvements = []

    # Check prompt length
    if len(prompt.prompt_text) < 20:
        review_parts.append("Prompt is too short and lacks detail")
        improvements.append("Add more context and specific requirements")
    elif len(prompt.prompt_text) > 1000:
        review_parts.append("Prompt is very long and may be overwhelming")
        improvements.append("Break into smaller, focused requests")

    # Check for common issues
    if not prompt.success and prompt.error_message:
        review_parts.append(f"Failed with error: {prompt.error_message}")
        improvements.append("Add error handling and retry logic to the prompt")

    # Check for vague language
    vague_words = ['something', 'somehow', 'maybe', 'perhaps', 'kind of']
    if any(word in prompt.prompt_text.lower() for word in vague_words):
        review_parts.append("Contains vague language that may cause confusion")
        improvements.append("Use specific, actionable language")

    # Check for missing context
    if 'please' not in prompt.prompt_text.lower() and 'help' in prompt.prompt_text.lower():
        review_parts.append("Request lacks polite context")
        improvements.append("Add 'please' and provide more context about the request")

    # Check for agent-specific improvements
    agent_specific = {
        'documentation-agent': {
            'keywords': ['docs', 'documentation', 'readme'],
            'suggestion': 'Specify documentation type (API, user guide, technical) and target audience'
        },
        'integration-agent': {
            'keywords': ['api', 'integration', 'external'],
            'suggestion': 'Include specific API endpoints, authentication requirements, and data formats'
        },
        'quality-agent': {
            'keywords': ['test', 'quality', 'validation'],
            'suggestion': 'Specify test types (unit, integration, e2e) and coverage requirements'
        }
    }

    agent_info = agent_specific.get(prompt.agent_name)
    if agent_info and not any(keyword in prompt.prompt_text.lower() for keyword in agent_info['keywords']):
        review_parts.append(f"Missing {prompt.agent_name} specific context")
        improvements.append(agent_info['suggestion'])

    # Default positive review
    if not review_parts:
        review_parts.append("Clear and well-structured prompt")
        improvements.append("Consider adding success criteria or expected outcomes")

    return {
        'review': '. '.join(review_parts),
        'improvement': '. '.join(improvements)
    }

def show_statistics():
    """Show prompt statistics"""
    stats = prompt_logger.get_prompt_stats()

    print("📊 PROMPT STATISTICS")
    print("=" * 30)
    print(f"Total prompts: {stats['total_prompts']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"Needs review: {stats['needs_review']}")
    print(f"\nAgent breakdown:")
    for agent, count in stats['agent_stats'].items():
        print(f"  {agent}: {count}")

def main():
    """Main PM review interface"""

    while True:
        print("\n🏢 PM PROMPT REVIEW TOOL")
        print("=" * 30)
        print("1. Review prompts needing attention")
        print("2. Show statistics")
        print("3. Exit")

        try:
            choice = input("\nSelect option (1-3): ").strip()

            if choice == '1':
                review_prompts()
            elif choice == '2':
                show_statistics()
            elif choice == '3':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break

if __name__ == "__main__":
    main()
