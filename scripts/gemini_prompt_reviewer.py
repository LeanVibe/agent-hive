#!/usr/bin/env python3
"""
Gemini Prompt Reviewer

Integrates Gemini CLI with the prompt review system to automatically
analyze and suggest improvements for agent prompts.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Add dashboard logging
sys.path.append(str(Path(__file__).parent.parent))


def run_gemini_review(prompt_text: str, agent_name: str) -> str:
    """Run Gemini CLI review on a prompt"""

    review_prompt = f"""
Analyze this AI agent prompt for effectiveness and suggest improvements:

AGENT: {agent_name}
PROMPT: {prompt_text}

Please assess:
1. Clarity and specificity
2. Actionability
3. Context sufficiency
4. Length appropriateness
5. Professional tone

Provide:
- Brief assessment (2-3 sentences)
- Specific improvement suggestions
- Rewritten version if needed

Focus on making the prompt more effective for AI agent communication.
"""

    try:
        result = subprocess.run([
            "gemini", "-p", review_prompt
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Gemini review failed: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Gemini review timeout - prompt may be too long"
    except Exception as e:
        return f"Error running Gemini review: {e}"


def review_prompts_needing_gemini() -> List[Dict]:
    """Review all prompts that need Gemini feedback"""

    try:
        from dashboard.prompt_logger import prompt_logger

        # Get prompts without Gemini feedback
        all_prompts = prompt_logger.get_recent_prompts(50)
        needs_gemini = [p for p in all_prompts if not p.gemini_feedback]

        results = []

        print(f"🤖 Found {len(needs_gemini)} prompts needing Gemini review")

        for i, prompt in enumerate(needs_gemini[:5], 1):  # Limit to 5 for demo
            print(f"\n🔍 Reviewing prompt {i}/{min(len(needs_gemini), 5)}")
            print(f"Agent: {prompt.agent_name}")
            print(f"Text: {prompt.prompt_text[:100]}...")

            # Run Gemini review
            gemini_feedback = run_gemini_review(
                prompt.prompt_text, prompt.agent_name)

            # Add to database
            prompt_logger.add_gemini_feedback(prompt.id, gemini_feedback)

            results.append({
                'prompt_id': prompt.id,
                'agent_name': prompt.agent_name,
                'feedback': gemini_feedback,
                'success': 'error' not in gemini_feedback.lower()
            })

            print(f"✅ Review completed for prompt {prompt.id}")

        return results

    except Exception as e:
        print(f"❌ Error reviewing prompts: {e}")
        return []


def generate_pm_suggestions(prompt_text: str, gemini_feedback: str) -> str:
    """Generate PM-style suggestions based on Gemini feedback"""

    # Extract key issues from Gemini feedback
    feedback_lower = gemini_feedback.lower()
    suggestions = []

    if 'unclear' in feedback_lower or 'vague' in feedback_lower:
        suggestions.append("Add more specific context and requirements")

    if 'long' in feedback_lower or 'verbose' in feedback_lower:
        suggestions.append("Break into smaller, focused requests")

    if 'urgent' in prompt_text.lower():
        suggestions.append(
            "Remove urgency language unless truly time-critical")

    if 'please' not in prompt_text.lower():
        suggestions.append("Add polite language (please, thank you)")

    if not suggestions:
        suggestions.append(
            "Prompt appears well-structured - consider adding success criteria")

    return ". ".join(suggestions)


def bulk_review_and_suggest():
    """Bulk review prompts and generate PM suggestions"""

    print("🚀 Starting bulk Gemini review and PM suggestion generation")
    print("=" * 60)

    results = review_prompts_needing_gemini()

    if not results:
        print("✅ No prompts need Gemini review")
        return

    print("\n📊 REVIEW SUMMARY:")
    print(f"Prompts reviewed: {len(results)}")
    successful_reviews = len([r for r in results if r['success']])
    print(f"Successful reviews: {successful_reviews}")

    # Generate PM suggestions for reviewed prompts
    try:
        from dashboard.prompt_logger import prompt_logger

        for result in results:
            if result['success']:
                # Get the updated prompt with Gemini feedback
                prompt = prompt_logger.get_recent_prompts(100)
                prompt_obj = next((p for p in prompt if p.id ==
                                  result['prompt_id']), None)

                if prompt_obj and not prompt_obj.pm_review:
                    # Generate PM suggestion
                    pm_suggestion = generate_pm_suggestions(
                        prompt_obj.prompt_text,
                        result['feedback']
                    )

                    # Add PM review
                    prompt_logger.add_pm_review(
                        result['prompt_id'],
                        f"Auto-generated based on Gemini feedback: {pm_suggestion}",
                        f"Consider: {pm_suggestion}")

                    print(
                        f"✅ Added PM suggestion for prompt {
                            result['prompt_id']}")

    except Exception as e:
        print(f"⚠️  Error generating PM suggestions: {e}")

    print("\n🎉 Bulk review completed!")
    print("Dashboard: http://localhost:8002")


def main():
    """Main CLI interface"""

    if len(sys.argv) > 1 and sys.argv[1] == "--bulk":
        bulk_review_and_suggest()
    else:
        print("Gemini Prompt Reviewer")
        print("Usage:")
        print("  python gemini_prompt_reviewer.py --bulk")
        print("  (Reviews prompts needing Gemini feedback)")


if __name__ == "__main__":
    main()
