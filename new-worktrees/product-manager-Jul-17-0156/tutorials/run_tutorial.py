#!/usr/bin/env python3
"""
Interactive Tutorial Runner for LeanVibe Agent Hive

This script provides a command-line interface for running interactive tutorials
with progress tracking, validation, and guided learning.
"""

import sys
import argparse
from pathlib import Path

# Add the tutorial framework to the path
sys.path.insert(0, str(Path(__file__).parent))

from framework.tutorial_manager import TutorialManager, DifficultyLevel
from framework.cli_interface import TutorialCLI
from framework.validation import StepValidator

def main():
    """Main entry point for tutorial runner."""
    parser = argparse.ArgumentParser(
        description="LeanVibe Agent Hive Interactive Tutorials",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tutorial.py                    # Launch interactive mode
  python run_tutorial.py --list             # List available tutorials
  python run_tutorial.py --tutorial getting-started  # Run specific tutorial
  python run_tutorial.py --difficulty beginner       # Filter by difficulty
        """
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List available tutorials'
    )

    parser.add_argument(
        '--tutorial',
        type=str,
        help='Run specific tutorial by ID'
    )

    parser.add_argument(
        '--difficulty',
        type=str,
        choices=['beginner', 'intermediate', 'advanced'],
        help='Filter tutorials by difficulty level'
    )

    parser.add_argument(
        '--user',
        type=str,
        default='default',
        help='User ID for progress tracking'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate tutorial content without running'
    )

    args = parser.parse_args()

    # Initialize tutorial manager
    tutorial_manager = TutorialManager()

    if args.list:
        list_tutorials(tutorial_manager, args.difficulty)
    elif args.tutorial:
        run_specific_tutorial(tutorial_manager, args.tutorial, args.user)
    elif args.validate:
        validate_tutorials(tutorial_manager)
    else:
        # Launch interactive CLI
        cli = TutorialCLI()
        cli.current_user = args.user
        cli.run()

def list_tutorials(manager: TutorialManager, difficulty_filter: str = None):
    """List available tutorials."""
    difficulty = DifficultyLevel(difficulty_filter) if difficulty_filter else None
    tutorials = manager.list_tutorials(difficulty)

    print("🎓 Available Tutorials:")
    print("=" * 50)

    if not tutorials:
        print("No tutorials found.")
        return

    for i, tutorial in enumerate(tutorials, 1):
        difficulty_emoji = {
            DifficultyLevel.BEGINNER: "🟢",
            DifficultyLevel.INTERMEDIATE: "🟡",
            DifficultyLevel.ADVANCED: "🔴"
        }

        print(f"{i}. {tutorial.metadata.title}")
        print(f"   {difficulty_emoji[tutorial.metadata.difficulty]} {tutorial.metadata.difficulty.value.title()} • {tutorial.metadata.estimated_time} min")
        print(f"   {tutorial.metadata.description}")
        print(f"   Prerequisites: {', '.join(tutorial.metadata.prerequisites) if tutorial.metadata.prerequisites else 'None'}")
        print()

def run_specific_tutorial(manager: TutorialManager, tutorial_id: str, user_id: str):
    """Run a specific tutorial by ID."""
    tutorial = manager.get_tutorial(tutorial_id)
    if not tutorial:
        print(f"❌ Tutorial '{tutorial_id}' not found.")
        return

    print(f"🚀 Starting tutorial: {tutorial.metadata.title}")

    # Start tutorial
    if manager.start_tutorial(user_id, tutorial_id):
        # Launch CLI with specific tutorial
        cli = TutorialCLI()
        cli.current_user = user_id
        cli.run_tutorial(tutorial_id)
    else:
        print("❌ Failed to start tutorial.")

def validate_tutorials(manager: TutorialManager):
    """Validate all tutorial content."""
    print("🔍 Validating tutorial content...")

    validator = StepValidator()
    all_valid = True

    for tutorial_id, tutorial in manager.tutorials.items():
        print(f"\n📋 Validating: {tutorial.metadata.title}")

        # Validate metadata
        if not tutorial.metadata.tutorial_id:
            print("  ❌ Missing tutorial_id")
            all_valid = False

        if not tutorial.metadata.title:
            print("  ❌ Missing title")
            all_valid = False

        if not tutorial.steps:
            print("  ❌ No steps defined")
            all_valid = False

        # Validate steps
        for step in tutorial.steps:
            if not step.step_id:
                print("  ❌ Step missing step_id")
                all_valid = False

            if not step.instructions:
                print(f"  ❌ Step {step.step_id} missing instructions")
                all_valid = False

            # Validate code examples syntax
            for example in step.code_examples:
                try:
                    compile(example, f"<tutorial-{tutorial_id}-{step.step_id}>", 'exec')
                except SyntaxError as e:
                    print(f"  ❌ Step {step.step_id} code example syntax error: {e}")
                    all_valid = False

        if all_valid:
            print("  ✅ Tutorial validation passed")

    if all_valid:
        print("\n🎉 All tutorials validated successfully!")
    else:
        print("\n❌ Some tutorials have validation errors.")
        sys.exit(1)

if __name__ == '__main__':
    main()
