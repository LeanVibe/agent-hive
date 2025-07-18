#!/usr/bin/env python3
"""Mock Gemini CLI for testing purposes."""

import argparse
import json
import random
import sys
import time
from datetime import datetime


def simulate_delay():
    """Simulate realistic CLI response time."""
    time.sleep(random.uniform(0.3, 1.5))


def simulate_review_response(prompt: str) -> dict:
    """Simulate successful Gemini review response."""
    review_types = [
        "code_review",
        "architecture_review",
        "performance_review",
        "security_review"
    ]

    feedback_examples = [
        "The code structure is well-organized and follows best practices.",
        "Consider adding error handling for edge cases.",
        "Performance looks good, but consider caching for frequently accessed data.",
        "Security review passed with no critical issues found.",
        "The implementation is solid but could benefit from additional documentation."
    ]

    return {
        "status": "success",
        "review_type": random.choice(review_types),
        "feedback": random.choice(feedback_examples),
        "score": random.uniform(7.0, 9.5),
        "suggestions": [
            "Add unit tests for edge cases",
            "Consider performance optimizations",
            "Update documentation"
        ],
        "timestamp": datetime.now().isoformat(),
        "model": "gemini-2.0-flash-thinking-exp-1219",
        "usage": {
            "input_tokens": len(prompt.split()),
            "output_tokens": random.randint(30, 150)
        }
    }


def simulate_error_response(error_type: str = "generic") -> dict:
    """Simulate error response."""
    error_messages = {
        "timeout": "Request timed out after 30 seconds",
        "rate_limit": "Rate limit exceeded. Please try again later.",
        "invalid_input": "Invalid input format for review",
        "service_unavailable": "Gemini service temporarily unavailable",
        "generic": "An unexpected error occurred"
    }

    return {
        "status": "error",
        "error": error_messages.get(error_type, error_messages["generic"]),
        "error_code": error_type,
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description="Mock Gemini CLI")
    parser.add_argument(
    "-p",
    "--prompt",
    required=True,
     help="Prompt to process")
    parser.add_argument("--error-type", help="Simulate specific error type")
    parser.add_argument(
    "--delay",
    type=float,
    default=0.8,
     help="Response delay in seconds")
    parser.add_argument(
    "--fail-rate",
    type=float,
    default=0.0,
     help="Failure rate (0.0-1.0)")

    args = parser.parse_args()

    # Simulate delay
    time.sleep(args.delay)

    # Simulate random failures
    if random.random() < args.fail_rate:
        response = simulate_error_response("generic")
        print(json.dumps(response, indent=2))
        sys.exit(1)

    # Simulate specific error if requested
    if args.error_type:
        response = simulate_error_response(args.error_type)
        print(json.dumps(response, indent=2))
        sys.exit(1)

    # Simulate success
    response = simulate_review_response(args.prompt)
    print(json.dumps(response, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
